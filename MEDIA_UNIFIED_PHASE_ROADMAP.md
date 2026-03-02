# MEDIA UNIFIED — FULL PHASE ROADMAP

Each phase is a separate Claude Code session. Do ONE phase, verify, commit, then start the next.
Every phase builds on the deployed `/media-unified` route from Phase 1.

---

## PHASE 1: Foundation ← START HERE (CLAUDE_CODE_MEDIA_UNIFIED_PHASE1.md)
- [x] Fix Proto_P avatar on Replit frontend
- [x] Git commit all pending work
- [ ] Telemetry Ribbon — live BTC price, fees, mempool, hashrate, F&G, block height, Signal Strength
- [ ] Deploy to `/media-unified` route (parallel to existing `/media`)

---

## PHASE 2: Intelligence Grid (SEPARATE SESSION)

### Section: Live Intelligence Columns (Nostr + X + Voice Intel)
Build the 3-column intelligence feed that was the centerpiece of media_terminal.html.

**Column 1 — Nostr Relay Feed:**
- Connect to 3+ Nostr relays via WebSocket (wss://relay.damus.io, wss://nos.lol, wss://relay.nostr.band)
- Subscribe to 6 OG Bitcoin pubkeys (Jack Dorsey, Lyn Alden, Adam Back, NVK, Saifedean, Preston Pysh)
- Render notes in real-time with avatar, name, timestamp, content, link to njump.me
- Green status dot when connected, count of notes received
- Auto-scroll, max 40 notes in DOM

**Column 2 — X Propagation:**
- Pull from `/api/media/feed` filtered by source_type='twitter'
- Same card format as Nostr but with X branding
- Link to original tweet
- Orange pulsing status indicator

**Column 3 — Voice Intel / Highlights:**
- Pull from `/api/media/feed` filtered for quotes/highlights
- Or pull from recent article summaries
- Rotating quotes from Bitcoin thought leaders

**Design:**
- 3 equal columns on desktop, stacked on mobile
- Each column has header with icon, name, status dot, count
- Feed items: dark card with subtle border, hover glow
- New items animate in from top with fade

**Verify:** All 3 columns show real data. Nostr WebSocket actually connects (check console).

---

## PHASE 3: Content Sections (SEPARATE SESSION)

### Section: Original Series (Podcast Video Series)
- Grid of series cards with YouTube thumbnails
- Click to expand episode panel with embedded YouTube player
- Episode list with scrollable sidebar
- Pull from `series_list` context variable (already passed by Flask route)

### Section: Cypherpunk'd Podcast
- Latest episodes in card grid
- Audio player bar (sticky bottom) — play/pause/stop
- Episode metadata: title, duration, episode number
- Pull from `latest_episodes` context variable

### Section: Essential Reading (Book Library)
- Categorized book grid: Series, Essentials, Bestsellers, Economics
- Book cards with colored spine, title, author
- Amazon affiliate links
- Expandable sections (Show More toggle)
- Pull from `all_books` context variable

**Verify:** All sections render with real data from Flask context. YouTube embeds load. Audio player works.

---

## PHASE 4: Reddit + Sentiment + Signal (SEPARATE SESSION)

### Feature: Reddit Bitcoin Feed
- Sidebar or section pulling from `/api/public/reddit-bitcoin`
- Thread cards with title, subreddit, score, comment count, time
- Link to Reddit thread
- Auto-refresh every 5 minutes

### Feature: Sentiment Dashboard
- Pull from `/api/media/sentiment`
- Visual gauge or bar showing bullish/bearish/neutral
- Historical sparkline if data available
- Color-coded (green/red/amber)

### Feature: Signal Strength Composite
- Combine: F&G index, sentiment, hashrate trend, fee trend, price momentum
- Single 0-100 score displayed prominently
- Animated ring/gauge visualization
- Brief text interpretation ("Accumulation zone" / "Caution: Euphoria" etc.)

**Verify:** Reddit shows real threads. Sentiment reflects actual API data. Signal score calculates from real inputs.

---

## PHASE 5: Health Strip + Newsletter + Polish (SEPARATE SESSION)

### Feature: System Health Strip
- Horizontal strip showing status of all PP services
- Green/amber/red dots for: Replit app, Ultron relay, Avatar server, Nostr relays, API endpoints
- Ping each service and show latency
- Auto-refresh every 60 seconds

### Feature: Newsletter Subscribe
- Email input + subscribe button
- POST to `/newsletter/subscribe`
- Success/error states with animation
- Clean, minimal design

### Feature: Final Polish
- Page transitions and scroll animations (subtle, not heavy)
- Mobile responsive pass — test at 375px, 768px, 1024px, 1440px
- Performance audit: lazy load images, debounce scroll handlers
- Accessibility: proper headings, alt text, focus states
- Meta tags: og:title, og:description, og:image for social sharing

### CUTOVER
- Change `/media` route in `routes.py` to render `media_unified.html` instead of `media_hub.html`
- Keep old route at `/media-legacy` as fallback
- Git commit + push
- Verify live site at protocolpulse.replit.app/media

---

## LINE COUNT TARGETS (quality benchmark)

| File | Target Lines | Rationale |
|------|-------------|-----------|
| media_unified.html | 800-1200 | Complex Jinja2 template with 7+ sections |
| media_unified.css | 2500-3500 | Bloomberg-quality design needs deep styling |
| media_unified.js | 1500-2000 | Nostr WebSocket, polling, sparklines, audio player, animations |
| **Total** | **4800-6700** | Must exceed old media_terminal.html (3021 lines) |

Current skeleton is 2823 lines total. That's 42-59% of minimum target. Each phase adds real depth.

---

## BANNED

- Three.js, VR, DAO, quantum auth, Sora, genetic algorithms
- localStorage (use JS variables/state)
- Paid API calls from frontend JS
- `-p` flag in Claude Code
- Placeholder/TODO/coming-soon content
- Claiming done without curl verification
