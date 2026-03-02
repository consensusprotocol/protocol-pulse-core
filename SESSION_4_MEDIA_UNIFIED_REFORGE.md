# SESSION 4: MEDIA UNIFIED REFORGE
# ================================================================
# Autonomous build. Create media_unified.html — a single world-class
# page that replaces media_hub.html (213 lines) and media_terminal.html
# (3021 lines). Everything lives in ONE template. No half measures.
# ================================================================

## INFRASTRUCTURE

REPLIT RELAY:
TOKEN=581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552
URL=https://protocolpulse.replit.app/api/admin/exec
Run Replit commands: curl -s -X POST "$URL" -H "Content-Type: aeries_count, latest_episodes, podcast_count, voice_count, all_books

**Existing services available:**
- `reddit_service` (global instance, PRAW initialized, has `get_trending_topics()`)
- `nostr_signal_service` (32 OG roster, signal scoring, demo mode available)
- `sentiment` via SentimentSnapshot model
- `FeedItem` model with source, source_type, tier, title, url, author, summary, verified
- `YouTubeService` for series/channel data

**BANNED:** Three.js, VR, DAO, quantum auth, Sora, genetic algorithms. No paid API calls from frontend JS. No localStorage (use React state or JS variables). No h-bitcoin')
def api_public_reddit_bitcoin():
    """Public endpoint for Bitcoin Reddit threads — no auth required."""
    try:
        limit = min(int(request.args.get('limit', 15)), 30)
        subreddits = ['bitcoin', 'bitcoindiscussion', 'lightningnetwork']
        posts = reddit_service.get_trending_topics(subreddits)
        if not posts:
            # Fallback: return from FeedItem table filtered by reddit
            items = FeedItem.query.filter(
                FeedItem.source_type == 'reddit'
            ).order_by(FeedItem.published_at.desc()).limit(limit).all()
            posts =ns' (body)
```

### Page Sections (TOP TO BOTTOM):

---

#### SECTION 1: HERO
Keep the existing hero design from media_hub.html — it's already premium quality.
- Drifting red grid, floating gradient orbs, scanline, vignette
- "The Network" title with italic gradient
- 4 metrics: Series count, Episode count, Book count, Live Notes
- Status indicators: green dot Nostr Relays, orange pulsing X Propagation
- **REMOVE** any "YT Transcripts" status line

---

#### SECTION 2: SIGNAL DASHBOARD (3-column live intelligence grid)
This is the CORE of the page. Three columns, side by side on desktop, stacked on mobile.

**Column 1: NOSTR SIGNAL FEED**
- Header: Purple (#a855f7) accent, "NOSTR" label, connection indicator dot
- Fetches from: `/api/nostr-signal/feed?limit=20`
- Each signal card shows:
  - OG name + tier badge (T1/T2/T3)
  - Classification badge (ALPHA=red, SIGNAL=orange, WATCH=blue, NOISE=gray)
  - Content text (truncated to 2 lines, expand on click)
  - Time ago label
  - Zap count + reply count
  - Category tag (mining, on-chain, macro, etc)
- Glass morphism cards: `background: rgba(8,8,14,0.8); backdrop-filter: blur(12px); border: 1px solid rgba(168,85,247,0.1);`
- Auto-refr verified badge if verified
  - If no X items exist, show the full media feed as "BITCOIN MEDIA FEED" instead
- Glass morphism cards with blue accent: `border: 1px solid rgba(59,130,246,0.1);`
- Each item links to external URL (opens in new tab)
- Auto-refresh every 90 seconds

**Column 3: REDDIT THREADS**
- Header: Orange/BTC (#f7931a) accent, "REDDIT" label
- Fetches from: `/api/public/reddit-bitcoin?limit=15`
- Each card shows:
  - Subreddit badge (r/bitcoin, r/lightningnetwork, etc)
  - Thread title (linked to reddit URL)
  - Author
  - Score (upvotes) + comment count
  - Time ago
- Glass morphism cards with orange accent: `border: 1px solid rgba(247,147,26,0.1);`
- If Reddit API returns empty (PRAW not configured), show graceful empty state: "Reddit feed connecting..." with spinning loader
- Auto-refresh every 120 seconds

**Mobile layout:** Stack 3 columns vertically with horizontal tab switcher at top (Nostr | Media | Reddit)

---

#### SECTION 3: SIGNAL STRENGTH COMPOSITE INDICATOR
A horizontal strip/bar that synthesizes all signals into one visual.

- Fetches from: `/api/media/sentiment`
- Displays:
  - Score (0-100) as a horizontal gauge/bar with gradient (red=fear, yelloes with inline player + episode sidebar
- Click series → expands with video player + episode list
- Each episode shows thumbnail, number, title
- Smooth navigation between episodes
- Use the `series_list` and `series_data` template variables already passed by the route

**FIX THE EPISODE CARD CLICK BUG:**
The existing code has a bug where clicking an episode doesn't show the info card. The issue is likely:
- The JavaScript event handler isn't binding to dynamically generated episode elements
- Or the episode detail panel HTML isn't being populated
- Debug by checking if the click handler firare broken (no cover_url in route data)**
The route data has NO `cover_url` field — they were stripped. The books only have: title, author, amazon_url, featured, category, color.

**Solution: Generate CSS-only book covers (no images needed):**
Each book card:
- Aspect ratio 2:3 (book proportion)
- Background: gradient using the book's `color` field
- Title text overlaid in white, author in smaller text below
- Category badge (Featured Series, Essential, Bestseller, Economics)
- Hover: subtle lift + glow
- Click → opens amazon_url in new tab

**Layout:**
- "Featured on CypherPunk'd" row (4 l, full width, dark glass, monospace text, green/red status dots.

---

## BUILD 3: UPDATE ROUTES

Modify routes.py to render the new template:

```python
@app.route('/media')
@app.route('/media-hub')
@app.route('/media-unified')
@app.route('/network')
def media_hub():
    """Media Unified — Protocol Pulse command center."""
    # ... keep all existing data fetching code ...
    return render_template('media_unified.html',
        series_list=series_list,
        series_data=series_config,
        series_count=len(series_config),
        latest_episodes=latest_episodes,
        podcast_count=podcast_count,
        voice_count=30,
        all_books=all_books,
    )
```

Change ONLY the template name from `media_hub.html` to `media_unified.html`. Add `/media-unified` and `/network` as aliases. Keep all the existing data fetching logic.

---

## BUILD 4: JAVASCRIPT REQUIREMENTS

All JS goes inside `{% block extra_js %}` in the template. No external JS files.

### Auto-refresh system:
```javascript
// Refresh feeds at different intervals
async function refreshNostr() {
    try {
        const r = await fetch('/api/nostr-signal/feed?limit=20');
        const data = await r.json();
        renderNostrFeed(data.signals || []);
    } catch(e) { console.warn('Nostr refresh failed:', e); }
}

async function refreshMediaFeed() {
    try {
        const r = await fetch('/api/media/feed?limit=20');
        const data = await r.json();
        renderMediaFeed(data || []);
    } catch(e) { console.warn('Media feed refresh failed:', e); }
}

async function refreshReddit() {
    try {
        const r = await fetch('/api/public/reddit-bitcoin?limit=15');
        const data = await r.json();
        renderRedditFeed(data || []);
    } catch(e) { console.warn('Reddit refresh failed:', e)javascript
function timeAgo(dateStr) {
    const now = new Date();
    const date = new Date(dateStr);
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff/60) + 'm ago';
    if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
    return Math.floor(diff/86400) + 'd ago';
}
```

### Mobile tab switcher:
```javascript
function switchFeedTab(tab) {
    document.querySelectorAll('.feed-col').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.feed-tab').forEach(el => el.classList.remove('rds">
            <div class="signal-header">
                <span class="og-name">${s.og_name}</span>
                <span class="tier-badge tier-${s.og_tier}">T${s.og_tier}</span>
                <span class="class-badge class-${s.classification.toLowerCase()}">${s.classification}</span>
                <span class="signal-time">${s.time_label || timeAgo(s.created_at)}</span>
            </div>
            <p class="signal-content">${escapeHtml(s.content)}</p>
            <div class="signal-meta">
                <span>⚡ ${s.zap_count || 0}</span>
                <span>💬 ${s.reply_couursor: default;
}
.signal-card:hover {
    background: rgba(14,14,22,0.9);
    border-color: rgba(255,255,255,0.08);
    transform: translateY(-1px);
}

/* Nostr accent */
.nostr-card { border-left: 2px solid rgba(168,85,247,0.3); }
.nostr-card:hover { border-left-color: rgba(168,85,247,0.6); }

/* X/Media accent */
.media-card { border-left: 2px solid rgba(59,130,246,0.3); }
.media-card:hover { border-left-color: rgba(59,130,246,0.6); }

/* Reddit accent */
.reddit-card { border-left: 2px solid rgba(247,147,26,0.3); }
.reddit-card:hover { border-left-color: rgba(247,147,26,0.6); }

/* Classifdc2626 0%, #f59e0b 30%, #ffffff 50%, #22c55e 70%, #10b981 100%);
    position: relative;
    width: 100%;
    max-width: 400px;
}
.sentiment-marker {
    position: absolute;
    top: -6px;
    width: 3px;
    height: 18px;
    background: var(--bright);
    border-radius: 2px;
    transition: left 1s ease;
    box-shadow: 0 0 8px rgba(255,255,255,0.5);
}

/* Book cards (CSS-only covers) */
.book-card {
    aspect-ratio: 2/3;
    border-radius: 6px;
    padding: 16px 12px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    position: relative;
    overflow: hidden;.2;
    margin-bottom: 4px;
}
.book-author {
    font-family: 'Geist Mono', monospace;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.6;
}
```

---

## BUILD 6: SIGNAL STRENGTH STRIP HTML PATTERN

```html
<section class="sec signal-strip">
    <div class="wrap">
        <div class="strip-inner">
            <div class="strip-label">
                <span class="mono sec-lab">SIGNAL STRENGTH</span>
            </div>
            <div class="strip-gauge">
                <div class="sentiment-gauge">
                    <div class="sentiment-marker" id="sentiment-marker" style="left:50%"></div>
                </div>
            </div>
            <div class="strip-state" id="sentiment-state">
                <span class="state-label">EQUILIBRIUM</span>
                <span class="state-score mono">50</span>
            </div>
            <div class="strip-keywords" id="sentiment-keywords"></div>
            <div class="strip-meta" id="sentiment-meta">
                <span class="mono" style="font-size:9px;color:var(--mut)">
                    Sample: <span id="sentiment-sample">0</span> · 
                    Verified: <span id="sentiment-verified">0</span> · 
                    Updated: <span id="sentiment-time">—</span>
                </span>
            </div>
        </div>
    </div>
</section>
```

---

## BUILD 7: PUSH TO REPLIT

After building media_unified.html locally, push to Replit via relay.

For files >1.5KB (media_unified.html will be large), use chunked Python writes:

```python
import base64, requests
TOKEN = "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"
URL = "https://protocolpulse.replit.app/api/admin/exec"

content = open("templates/media_unified.html", "rb").read()
b64 = base64.b64encode(content).decode()
chunk_size = 1000
chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]

# Write first chunk (create file)
requests.post(URL, json={"token": TOKEN, "cmd": f"python3 -c \"import base64; open('templates/media_unified.html','wb').write(base64.b64decode('{chunks[0]}'))\""})

# Append remaining chunks
for chunk in chunks[1:]:
    requests.post(URL, json={"token": TOKEN, "cmd": f"python3 -c \"import base64; open('templates/media_unified.html','ab').write(base64.b64decode('{chunk}'))\""})
```

### Route changes (use sed on Replit):
```bash
# Add /media-untemplates/media_hub.html.bak
cp templates/media_terminal.html templates/media_terminal.html.bak
```

---

## BUILD 8: VERIFICATION CHECKLIST

```bash
# 1. Page loads
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/media")
echo "Media page: $STATUS"  # Must be 200

# 2. Media unified renders (not old template)
curl -s "https://protocolpulse.replit.app/media" | grep -c "SIGNAL STRENGTH"
# Must return 1+

# 3. Reddit API works
curl -s "https://protocolpulse.replit.app/api/public/reddit-bitcoin?limit=3" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
# Must return > 0

# 4. Nostr feed loads
curl -s "https://protocolpulse.replit.app/api/nostr-signal/feed?limit=3" | grep -c "signals"
# Must return 1

# 5. All aliases work
for route in /media /media-hub /media-unified /network; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app$route")
  echo "$route: $code"
done
# All must be 200

# 6. Key sections present in HTML
curl -s "https://protocolpulse.replit.app/media" | grep -c "nostr-feed\|media-feed\|reddit-feed\|sentiment-gauge\|book-card"
# Must return 3+

# 7. No broken references
curl -s "https://protocolpulse.replit.app/media" | grep -c "media_hub.html\|media_terminal.html"
# Must return 0 (old templates not referenced)
```

---

## BUILD 9: GIT COMMIT & PUSH

```bash
cd ~/workspace
git add -A
git commit -m "Session 4: Media Unified Reforge — single page with live Nostr/Media/Reddit feeds, Signal Strength, CSS book covers, glass morphism UI"
git push origin main
```

---

## QUALITY CHECKLIST (What makes this WORLD CLASS):

1. **NO FAKE DATA** — Every feed pulls from a real API endpoint. Demo data is labeled "DEMO".
2. **GLASS MORPHISM** — Every card uses backdrop-filter blur, subtle borders, hover lift.
3. **COLOR CONSISTENCY** — Nostr=purple, X/Media=blue, Reddit=orange, Bitcoin=gold, Status=red.
4. **TYPOGRAPHY HIERARCHY** — Instrument Serif for section titles, Geist Mono for data/labels, DM Sans for body text.
5. **MOBILE-FIRST** — Tab switcher on mobile for the 3-column feed. Everything stacks cleanly.
6. **ANIMATIONS** — Subtle fadeUp on load, smooth hover transitions, pulsing status dots.
7. **AUTO-REFRESH** — Feeds update silently in the background. No page reload needed.
8. **PERFORMANCE** — No Three.js, no heavy libraries. Pure CSS + vanilla JS.
9. **B