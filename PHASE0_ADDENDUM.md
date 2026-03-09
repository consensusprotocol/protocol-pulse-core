# PHASE 0 ADDENDUM — p3-media-unified
## Created: 2026-03-09 | Status: INCORPORATED

---

## TOP ADDITIONS FROM SYNTHESIS — IMPLEMENTATION PLAN

### 1. AI Meta-Briefing Card (P0 — HIGHEST IMPACT)
**What:** Daily AI synthesis card that condenses top 5 articles into a 3-sentence intel brief
**How:** `/api/media/meta-briefing` endpoint using Claude Haiku (`claude-haiku-4-5-20251001`)
- Cached 24h in-process dict (keyed by date string)
- Passes top 5 article titles+summaries to Claude
- Returns JSON: `{ brief, headline, stance, cached_at }`
- Displayed as gold-bordered card in hero section with "AI INTEL BRIEF" kicker
- Graceful fallback: show placeholder if API unavailable

### 2. Feed Mode Tabs (P0 — Personalization proxy)
**What:** Netflix-style mode switcher above articles: ALL / MARKETS / MINING / REGULATION / SOVEREIGNTY / LIGHTNING
**How:** Pure JS category filter — no reload
- Adds `data-category` attrs to all article cards
- Active tab: red underline + red bg tint
- Simultaneous filter across ALL content rows (articles, highlights, trending)
- State preserved in `localStorage` across visits

### 3. Enhanced Command Palette v2 (P0 — Power user UX)
**What:** Cmd+K evolves from search to full command center
**How:** Detect `> ` prefix for filter commands:
- `> filter mining` → activates mining tab filter
- `> filter markets` → activates markets tab
- `> filter [topic]` → filters by topic
- `> clear` → reset filters
- Without `> ` prefix: semantic search
- Returns ranked article results from `/api/media/semantic-search`

### 4. SSE Production-Grade Architecture (P0 — Real-time reliability)
**What:** `/api/stream/media-feed` with heartbeat, Last-Event-ID, reconnect
**How:**
- 25s heartbeat: `: keepalive\n\n`
- `id:` field on every data event for Last-Event-ID resume
- Event types: `btc_price_update`, `new_article`, `sentiment_update`, `telemetry`
- Max connection duration: 600s with graceful close
- Browser: `EventSource` with onerror reconnect + 30s polling fallback
- Rate: sends real data update every 30s

### 5. Semantic Search with Rate Limiting (P1 — Core interaction)
**What:** `/api/media/semantic-search` with Claude Haiku ranking + 5min cache
**How:**
- Rate limit: 10 requests/minute per IP (in-process bucket)
- Query length cap: 200 chars max
- Cache: `{normalized_query: {results, cached_at}}` dict, 5min TTL
- Claude Haiku ranks article titles by relevance to query
- Fallback: SQLite LIKE search if API unavailable
- Returns top 10 results with `relevance_score` field

### 6. System Health Endpoint (P1 — Observability)
**What:** `/api/system-health` returns service status JSON
**How:**
- Flask app status
- Last article ingest time
- Article count (24h)
- DB connectivity check
- ElevenLabs API reachability (cached 5min)
- Returns `{ status, services, articles_24h, last_render_time }`

### 7. Ambient Intelligence UI (P1 — Living system feel)
**What:** UI elements respond to data velocity
**How:**
- Signal strength arc pulsing animation (CSS keyframes) tied to score
- Trending topic pills gently reorder on page load based on recency
- BTC 7-day sparkline (canvas 2D) — red line, no external lib
- Pulse indicator on telemetry ribbon changes speed based on signal strength
- Articles with `direction=bullish` get subtle green left-border tint

### 8. "NEW" Badge + Read Time Estimates (P1 — Engagement)
**What:** Visual cues on article cards
**How:**
- Articles published < 6hrs ago: red "NEW" pill badge
- Read time: `Math.ceil(word_count / 200)` min (estimated from excerpt length × 4)
- Category badge rendered from `article.category` with color mapping

### 9. Keyboard Navigation (P1 — Power user accessibility)
**What:** J/K to move between cards, Enter to open, Esc to close overlay
**How:**
- Global keydown listener on `.mu-card` elements
- `[data-keyboard="true"]` attribute marks navigable elements
- Visual focus ring: 1px solid rgba(255,51,51,0.6) + subtle glow
- Tab order: telemetry → tabs → hero → articles → episodes

### 10. Progressive Media + PWA (P2 — Performance)
**What:** Lazy loading + PWA install support
**How:**
- `IntersectionObserver` on all images + card sections
- `loading="lazy"` + `decoding="async"` on all images
- `fetchpriority="high"` on hero media only
- `content-visibility: auto` on off-screen sections
- Base.html already includes `manifest.json` link — no change needed

---

## UNANIMOUS P0 GAPS ADDRESSED:
✅ AI Intelligence Layer → Meta-Briefing card + semantic search
✅ Feed Personalization → Mode tabs (Latest/High Signal/etc.)
✅ Entity Graph hints → Trending topic pills from real DB
✅ SSE Reliability → Heartbeat + Last-Event-ID + reconnect
✅ Rate Limiting → Search endpoint protection
✅ Cross-Device → localStorage state persistence

## CONFIRMED SPEC STRENGTHS (preserved):
✅ Real-time SSE architecture
✅ Clean visual consolidation
✅ Glassmorphism aesthetic
✅ Mobile-first CSS Grid
✅ Performance optimization (lazy load, content-visibility)

## DESCOPED (too complex for single session, Phase 2+):
- Vector DB personalization (requires new infrastructure)
- IPFS content caching (external dependency)
- Multi-LLM synthesis engine (cost + complexity)
- zk-SNARK privacy layer (research-stage)
- WebTransport upgrade (low browser support)
