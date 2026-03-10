# SESSION 1 — PULSE TERMINAL: COMPLETE BUILD SPEC v2
# Bloomberg-style Bitcoin intelligence terminal
# Architecture: Free teaser tier → $29/mo Commander unlock
# The terminal IS the product. The lock IS the sales funnel.

---

## PRODUCT PHILOSOPHY — READ THIS BEFORE TOUCHING CODE

The free terminal is the best free Bitcoin terminal on the internet.
It is beautiful, dense, live, and deliberately incomplete.

Every locked panel is a billboard.
The blur is not a barrier — it is an invitation.
The lock icon is not a wall — it is a preview of what's behind it.

The moment a user sees the Signal Intelligence score blurred behind a lock
and reads "PP SIGNAL: 74 — BULLISH" in ghosted text they can almost make out —
that is the moment they reach for their card.

$29/mo is an impulse purchase. It must feel that way.
The upgrade path is: see locked data → feel the pain of not knowing → one click to Commander.

Commander users get:
- Full Signal Intelligence score + all sub-components (the crown jewel)
- Full on-chain metrics: MVRV, S2F, exchange flows, realized price
- Trending topics + article velocity from 80-channel scan
- Early warning alert feed (price moves, sentiment shifts, breaking news)
- Raw API access (10,000 req/hr) — included, not the headline
- No ads, no rate limits on the web terminal

Free users get:
- BTC price + full market data panel (always live, always real)
- Mempool + fee market (always live, always real)  
- Fear & Greed index (always live, always real)
- Teased previews of everything else — blurred, ghosted, locked
- The upgrade CTA woven naturally into every locked panel

---

## VISUAL DESIGN SYSTEM — BLOOMBERG TERMINAL AESTHETIC

### Color palette (exact hex — zero deviations):
```
BG_BASE:        #080810   (main page background)
BG_PANEL:       #0D0D1A   (individual panel backgrounds)
BG_HEADER:      #050508   (top status bar, absolute black)
BORDER:         #1C1C2E   (all panel borders, grid lines)
TEXT_PRIMARY:   #E2E8F0   (main data values)
TEXT_LABEL:     #64748B   (field labels, units — muted)
TEXT_DIM:       #2D3748   (inactive, placeholder)
GOLD:           #F59E0B   (BTC price, key metrics, Commander badge)
GREEN:          #10B981   (positive deltas, bullish signals)
RED:            #EF4444   (negative deltas, bearish signals, alerts)
CYAN:           #22D3EE   (LIVE indicators, streaming dots, API)
AMBER:          #FB923C   (warnings, mid signals, fee levels)
LOCKED_BLUR:    rgba(8,8,16,0.85) (the blur overlay on locked panels)
LOCKED_BORDER:  #F59E0B at 30% opacity (golden glow on locked panels)
PHOSPHOR:       #00FF41   (API response viewer only — classic terminal green)
```

### Typography — monospace everything:
```css
--font-terminal: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;

/* Usage */
.data-value   { font: 600 13px/1 var(--font-terminal); }
.data-label   { font: 400 9px/1 var(--font-terminal); text-transform: uppercase; letter-spacing: 0.08em; }
.panel-title  { font: 700 11px/1 var(--font-terminal); text-transform: uppercase; letter-spacing: 0.12em; }
.hero-price   { font: 700 36px/1 var(--font-terminal); }
.api-response { font: 400 12px/1.6 var(--font-terminal); color: #00FF41; }
```
Zero sans-serif anywhere on this page. This is a terminal. Every character is monospace.

### Layout:
```
Desktop ≥1440px:  4-column grid, 8px gap
Laptop  1024-1439: 3-column grid, 8px gap  
Tablet  768-1023:  2-column grid, 6px gap
Mobile  ≤767px:    1-column, panels stack
Panel padding:     14px
Border-radius:     0px on panels (Bloomberg has zero radius)
Panel border:      1px solid var(--border)
```

### Locked panel treatment (CRITICAL — this drives conversions):
```css
.panel-locked {
  position: relative;
  border: 1px solid rgba(245, 158, 11, 0.25);  /* subtle gold glow */
}
.panel-locked .panel-content {
  filter: blur(4px);
  user-select: none;
  pointer-events: none;
  opacity: 0.4;
}
.panel-locked .lock-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(8, 8, 16, 0.75);
  backdrop-filter: blur(2px);
  gap: 8px;
}
.lock-overlay .lock-icon   { font-size: 20px; color: #F59E0B; }
.lock-overlay .lock-tier   { font: 700 10px var(--font-terminal); color: #F59E0B; letter-spacing: 0.15em; }
.lock-overlay .lock-cta    { font: 400 10px var(--font-terminal); color: #94A3B8; }
.lock-overlay .lock-button {
  margin-top: 4px;
  padding: 6px 14px;
  background: transparent;
  border: 1px solid #F59E0B;
  color: #F59E0B;
  font: 600 10px var(--font-terminal);
  letter-spacing: 0.1em;
  cursor: pointer;
  text-transform: uppercase;
}
.lock-overlay .lock-button:hover { background: #F59E0B; color: #080810; }
```

The locked data MUST be real data behind the blur — not placeholder text.
When a user inspects element they should see actual MVRV values, real signal scores.
This builds trust. The product is real. The lock is just the paywall.

### Signature UI elements:

**1. Top status bar (fixed, 36px, full-width):**
```
[PROTOCOL PULSE TERMINAL]    BTC $85,420 ▲2.34%    [● LIVE]  15:42:07 UTC
```
- Background: #050508
- Left text: PHOSPHOR green, monospace
- Center BTC price: GOLD, updates in real-time, flashes white on change
- Right: cyan pulsing dot + UTC clock ticking every second
- Bottom border: 1px solid rgba(34,211,238,0.2)
- On scroll: stays fixed at top

**2. Panel anatomy (every panel follows this exactly):**
```
┌─────────────────────────────────────────────────┐
│ PANEL TITLE                   UPDATED 15:42:01  │  ← header bar, BG_PANEL darker
├─────────────────────────────────────────────────┤
│                                                 │
│  data content here                              │
│                                                 │
└─────────────────────────────────────────────────┘
```
Header: 28px tall, border-bottom 1px solid BORDER
Title: uppercase, TEXT_LABEL color
Timestamp: right-aligned, TEXT_DIM, updates when data refreshes

**3. Data rows (all data displayed this way):**
```
LABEL                          VALUE    DELTA
```
Label: left-aligned, 9px, TEXT_LABEL
Value: right-aligned, 13px, TEXT_PRIMARY (or GOLD for BTC values)
Delta: right of value, 10px, GREEN/RED with ▲/▼ prefix

**4. Sparklines:**
Inline SVG, 80px × 20px, no axes, no labels.
Just the line. Stroke 1.5px.
Gold for price history, cyan for network metrics, green for sentiment.

**5. Live pulse animation:**
```css
@keyframes pulse-live {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.live-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #22D3EE;
  animation: pulse-live 2s ease-in-out infinite;
}
```
Every panel with live data gets this dot next to its title.

**6. Value flash on update:**
```css
@keyframes value-flash {
  0% { color: #FFFFFF; }
  100% { color: var(--text-primary); }
}
.value-updated { animation: value-flash 0.6s ease-out; }
```
Any data value that changes triggers this class for 600ms.

---

## FULL PANEL LAYOUT — FREE vs LOCKED

### TOP STATUS BAR (always free)
Fixed. Full width. Never scrolls away. 36px.

---

### ROW 1 — MARKET OVERVIEW (all FREE)

**Panel 1A — BTC PRICE** [spans 2 cols desktop, 1 col mobile]
```
BTC / USD                                    ● LIVE
──────────────────────────────────────────────────
$85,420.00
──────────────────────────────────────────────────
24H CHANGE     ▲ $1,942      ▲ 2.34%
7D CHANGE      ▲ $6,480      ▲ 8.21%
30D CHANGE     ▲ $11,020     ▲ 14.79%
──────────────────────────────────────────────────
24H HIGH       $87,100       24H LOW    $83,200
MKT CAP        $1.68T        DOMINANCE  54.2%
[sparkline 7-day price]
```
Source: mempool.space WebSocket (real-time, sub-second)
Refresh: live stream, no polling

**Panel 1B — MEMPOOL** [1 col]
```
MEMPOOL                                      ● LIVE
──────────────────────────────────────────────────
UNCONFIRMED TXS      142,831
MEMPOOL SIZE         287.4 MB
──────────────────────────────────────────────────
FEE MARKET (sat/vB)
  NO PRIORITY          1
  LOW PRIORITY         4
  MED PRIORITY        12
  HIGH PRIORITY       28
──────────────────────────────────────────────────
NEXT BLOCK ETA        ~8 min
BLOCKS BEHIND            14
[fee market sparkline 24h]
```
Source: mempool.space API
Refresh: 30s

**Panel 1C — FEAR & GREED** [1 col]
```
FEAR & GREED INDEX                           ○ 15M
──────────────────────────────────────────────────
TODAY                72 / 100
CLASSIFICATION       GREED
──────────────────────────────────────────────────
  [ASCII gradient bar]
  FEAR ░░░░▓▓▓▓▓▓▓▓▓▓▓ GREED
  0         50        100
                      ↑72
──────────────────────────────────────────────────
YESTERDAY            68  ▲ +4
LAST WEEK            71  ▲ +1
LAST MONTH           45  ▲ +27
```
Source: alternative.me API
Refresh: 15min (cached)

---

### ROW 2 — ON-CHAIN METRICS (LOCKED for free users)

**Panel 2A — HASHRATE & DIFFICULTY** [LOCKED]
Lock text: "NETWORK SECURITY DATA — COMMANDER"
Behind blur: real hashrate, difficulty, next adjustment countdown
```
NETWORK SECURITY                    🔒 COMMANDER
──────────────────────────────────────────────────
HASHRATE         ██████ EH/s    ▲ █.█%
DIFFICULTY       ████.██ T      ▲ █.█%
──────────────────────────────────────────────────
NEXT ADJUSTMENT  +█.█%   in  █d █h █m
BLOCK HEIGHT     ███,███
LAST BLOCK       █ min ago
[sparkline — blurred]
```
Lock overlay: "UNLOCK NETWORK SECURITY DATA — $29/MO"

**Panel 2B — MVRV Z-SCORE** [LOCKED]
Lock text: "VALUATION MODEL — COMMANDER"
Behind blur: real MVRV, realized price, zone classification
```
VALUATION MODEL                     🔒 COMMANDER
──────────────────────────────────────────────────
MVRV Z-SCORE         █.██
SIGNAL               ████████
──────────────────────────────────────────────────
REALIZED PRICE    $██,███
REALIZED CAP      $███B
[zone diagram — blurred]
```
Lock overlay: "SEE WHERE WE ARE IN THE CYCLE — $29/MO"

**Panel 2C — STOCK TO FLOW** [LOCKED]
Behind blur: real S2F ratio, model price, halving countdown
Lock overlay: "S2F MODEL + HALVING COUNTDOWN — $29/MO"

**Panel 2D — EXCHANGE FLOWS** [LOCKED]
Behind blur: real inflow/outflow/net, exchange reserves
Lock overlay: "FOLLOW SMART MONEY — $29/MO"

---

### ROW 3 — PP SIGNAL INTELLIGENCE (crown jewel — LOCKED)

This is the section that makes people subscribe.
The free user sees enough to understand what it is — not enough to use it.

**Panel 3A — SIGNAL SCORE** [spans 2 cols, LOCKED with special treatment]

This panel gets a MORE prominent lock treatment than others.
The blur is slightly less opaque (0.6 vs 0.85) so they can ALMOST read the number.
The number is large. The classification is large. They can tell it says "BULLISH."
They just can't read the exact score or sub-components.

```
PP SIGNAL INTELLIGENCE          🔒 COMMANDER EXCLUSIVE
──────────────────────────────────────────────────────────
                                              ● LIVE

    ██ / 100    [BULLISH]    ▲ +3 FROM YESTERDAY

──────────────────────────────────────────────────────────
COMPONENT BREAKDOWN
  ARTICLE SENTIMENT     ██ / 100   ████████░░
  PRICE MOMENTUM        ██ / 100   ██████░░░░
  SOCIAL VOLUME         ██ / 100   ███████░░░
  ON-CHAIN HEALTH       ██ / 100   ████████░░
  FEAR/GREED CONTRIB    ██ / 100   ███████░░░
──────────────────────────────────────────────────────────
[sparkline 7-day signal history — blurred]
```

Lock overlay (special — centered, more prominent than others):
```
╔══════════════════════════════════════════╗
║  🔒  PP SIGNAL INTELLIGENCE              ║
║                                          ║
║  The only composite Bitcoin signal       ║
║  built from 80 live sources.             ║
║  Updated every 2 minutes.               ║
║                                          ║
║  [ UNLOCK FOR $29/MO ]                   ║
╚══════════════════════════════════════════╝
```
The copy matters here: "the only composite Bitcoin signal built from 80 live sources" — that's true and it's the value prop in 12 words.

**Panel 3B — TRENDING TOPICS** [LOCKED]
```
TRENDING INTEL (LAST 2H)            🔒 COMMANDER
──────────────────────────────────────────────────
01  ████ █████          ↑↑↑  ██ articles
02  ███████            ↑↑   ██ articles
03  ██████ ██████      ↑    ██ articles
[3 more rows — fully blurred]
──────────────────────────────────────────────────
TOTAL ARTICLES TODAY    ███
SOURCES MONITORED        80
```
Lock overlay: "80 SOURCES. RANKED BY VELOCITY. $29/MO"

**Panel 3C — EARLY WARNING FEED** [LOCKED]
```
EARLY WARNINGS                      🔒 COMMANDER
──────────────────────────────────────────────────
[15:38] ████████████████████████...
[15:21] ████████████████████████...
[14:57] ████████████████████████...
[14:44] ████████████████████████...
[14:31] ████████████████████████...
──────────────────────────────────────────────────
```
Lock overlay: "KNOW BEFORE TWITTER DOES — $29/MO"

---

### ROW 4 — LATEST INTEL (FREE — drives article page traffic)

**Panel 4A — LATEST ARTICLES** [spans full width, FREE]
```
LATEST INTEL                                 ● LIVE
──────────────────────────────────────────────────
[15:42]  BlackRock adds 2,340 BTC to spot ETF holdings...       →
[15:31]  Fed minutes signal rate hold through Q2 2026...        →
[15:18]  Mining difficulty rises 3.4% — strongest in 6 months  →
[15:07]  Mempool clears after weekend congestion spike          →
[14:54]  Strategy (MSTR) announces convertible note offering    →
──────────────────────────────────────────────────
→ VIEW ALL 1,300+ ARTICLES
```
Source: PP article feed, latest 5, auto-refresh 60s
Each row is a clickable link to the full article.

---

### ROW 5 — MACRO CONTEXT (partial free / partial locked)

**Panel 5A — MACRO SIGNALS** [FREE — basic only]
```
MACRO CONTEXT                                ○ 1H
──────────────────────────────────────────────────
DXY (USD INDEX)    101.4    ▼ -0.2%
GOLD               $2,340   ▲ +0.8%
S&P 500            5,842    ▲ +0.4%
──────────────────────────────────────────────────
BTC/GOLD RATIO     36.5
BTC/SP500 RATIO    14.6
```
Source: free market data APIs

**Panel 5B — LIGHTNING NETWORK** [LOCKED]
```
LIGHTNING NETWORK                   🔒 COMMANDER
──────────────────────────────────────────────────
NODES         ██,███     ▲ ███
CHANNELS      ██,███     ▼ ███
CAPACITY    █,███  BTC
[sparkline — blurred]
```
Lock overlay: "LN NETWORK HEALTH — COMMANDER"

---

### UPGRADE CTA SECTION (between Row 4 and Row 5 — always visible)

This is NOT a modal. NOT a popup. It's an inline section, part of the page.
Designed to feel like part of the terminal, not an ad.

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  COMMANDER ACCESS                                        $29/MO  ║
║  ─────────────────────────────────────────────────────────────  ║
║  ✓  PP Signal Intelligence — composite score from 80 sources    ║
║  ✓  Full on-chain metrics (MVRV, S2F, exchange flows)           ║
║  ✓  Trending topics ranked by velocity                          ║
║  ✓  Early warning alert feed                                    ║
║  ✓  API access — 10,000 req/hr                                  ║
║  ✓  No rate limits on this terminal                             ║
║                                                                  ║
║  [ ACTIVATE COMMANDER → $29/MO ]    [ SEE WHAT YOU'RE MISSING ] ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```
- Background: #0D0D1A
- Border: 1px solid rgba(245,158,11,0.4) — subtle gold
- The "ACTIVATE COMMANDER" button: solid GOLD background, black text, full monospace
- The "SEE WHAT YOU'RE MISSING" button: transparent, gold border, gold text
  → This button triggers a mode where all locked panels briefly unblur for 3 seconds
  → After 3 seconds they re-lock with "That was Commander access. Want it permanently?"
  → This is the single most important conversion mechanic on the page

---

## API ARCHITECTURE — BACKEND

### Endpoints that power the terminal (all under /api/v2/terminal/):

```python
# FREE endpoints — no auth, 60 req/hr per IP
GET /api/v2/terminal/price        # BTC price, change, market cap, dominance
GET /api/v2/terminal/mempool      # pending txs, size, fee tiers, next block
GET /api/v2/terminal/fear-greed   # today, yesterday, week, month
GET /api/v2/terminal/latest       # last 5 PP articles with title, time, slug
GET /api/v2/terminal/macro        # DXY, gold, S&P, ratios

# COMMANDER endpoints — require Bearer token, 10k req/hr
GET /api/v2/terminal/signal       # Signal score 0-100 + all sub-components
GET /api/v2/terminal/topics       # trending topics ranked by velocity
GET /api/v2/terminal/alerts       # early warning feed, last 20
GET /api/v2/terminal/onchain      # MVRV, S2F, hashrate, difficulty, exchange flows
GET /api/v2/terminal/lightning    # LN nodes, channels, capacity

# API key management
POST /api/v2/terminal/keys        # generate new key (requires active subscription)
GET  /api/v2/terminal/keys        # list user's keys
DELETE /api/v2/terminal/keys/<id> # revoke key
```

### Signal Intelligence computation (the crown jewel):
```python
def compute_signal_score():
    components = {
        "article_sentiment":  get_article_sentiment_score(),   # 0-100
        "price_momentum":     get_price_momentum_score(),      # 0-100  
        "social_volume":      get_social_volume_score(),       # 0-100
        "onchain_health":     get_onchain_health_score(),      # 0-100
        "fear_greed_contrib": get_fear_greed_score(),          # 0-100
    }
    weights = {
        "article_sentiment": 0.30,
        "price_momentum":    0.25,
        "social_volume":     0.15,
        "onchain_health":    0.20,
        "fear_greed_contrib":0.10,
    }
    score = sum(components[k] * weights[k] for k in components)
    classification = classify_signal(score)  # EXTREME FEAR / FEAR / NEUTRAL / BULLISH / EXTREME BULLISH
    return {"score": round(score), "classification": classification, "components": components, "timestamp": utcnow()}
```
Cached in Redis/memory for 2 minutes. Recomputed on cache expiry.

---

## COMMANDER SUBSCRIPTION FLOW

### Page: /terminal/commander (NOT /premium — the terminal owns its own upgrade path)

1. User clicks "ACTIVATE COMMANDER" anywhere on /terminal
2. Redirects to /terminal/commander (or opens inline modal — CC decides which is cleaner)
3. Shows: price ($29/mo), feature list, Stripe Checkout button
4. Stripe Checkout → success → POST /api/v2/terminal/activate → create API key → show key
5. User is now Commander — terminal re-renders with all panels unlocked
6. API key shown once at activation with copy button + "store this securely" warning
7. Key also available at /terminal/account page

### Auth state:
```
not_logged_in   → show terminal with locks, prompt to create account to subscribe
logged_in_free  → show terminal with locks, show upgrade CTA
commander       → show full terminal, show API key panel at bottom
```
Session-based auth (Flask-Login, already in place).
Commander status stored as `user.tier = 'commander'` in DB.

---

## THE "SEE WHAT YOU'RE MISSING" MECHANIC (most important UX detail)

When a free user clicks this button:
```javascript
function previewCommander() {
  const lockedPanels = document.querySelectorAll('.panel-locked');
  lockedPanels.forEach(panel => {
    panel.classList.add('preview-mode');
  });
  
  // Show countdown
  let countdown = 5;
  const timer = setInterval(() => {
    countdown--;
    updateCountdown(countdown);
    if (countdown <= 0) {
      clearInterval(timer);
      lockedPanels.forEach(panel => panel.classList.remove('preview-mode'));
      showReEngagementBanner(); // "That was 5 seconds of Commander. Want it permanently? $29/mo"
    }
  }, 1000);
}
```
```css
.panel-locked.preview-mode .panel-content {
  filter: none;
  opacity: 1;
  transition: filter 0.3s ease, opacity 0.3s ease;
}
.panel-locked.preview-mode .lock-overlay {
  opacity: 0;
  pointer-events: none;
}
```
During preview: a gold countdown bar at the top of each panel ticks from 5 to 0.
After preview: panels re-lock with smooth transition.
Re-engagement banner appears at top of page:
"You just saw Commander access for 5 seconds. Never lose that again. → $29/MO"

This mechanic is the single highest-converting element on the page.
It is NOT optional. It MUST be in the build.

---

## REAL-TIME DATA ARCHITECTURE

### WebSocket for live price:
```javascript
const ws = new WebSocket('wss://ws.blockchain.info/inv');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.op === 'utx') updatePrice(data.x);
};
// Fallback: poll /api/v2/terminal/price every 15s if WS fails
```

### Polling schedule:
```
BTC price:      WebSocket (live) / 15s poll fallback
Mempool:        30s
Fear & Greed:   15min (API rate limit)
Macro:          60min
Articles:       60s
Signal score:   2min (computation cost)
On-chain:       5min
Topics:         5min  
Alerts:         30s (Commander only)
```

### Data freshness indicators:
- `● LIVE` — WebSocket/sub-30s: pulsing cyan dot
- `○ 1H` — hourly refresh: dim static dot + interval label
- `○ 15M` — 15-min refresh: dim static dot
- All timestamps update in real-time relative to now: "2 min ago" → "3 min ago"

---

## CC BUILD INSTRUCTIONS

### Step 1 — Read existing terminal route and v30 branch code:
```bash
grep -n "terminal" ~/protocol_pulse/core/routes.py | head -20
cat ~/protocol_pulse/core/routes.py | grep -A 30 "def.*terminal"
```

### Step 2 — Create the template:
File: `~/protocol_pulse/core/templates/terminal.html`
Single-file: all CSS inline in `<style>`, all JS inline in `<script>`.
NO external CSS frameworks. NO Bootstrap. NO Tailwind. Pure CSS.
JetBrains Mono from Google Fonts CDN only.
Chart.js from CDN for sparklines only.

### Step 3 — Backend signal computation:
Add to `~/protocol_pulse/core/services/` a new `signal_engine.py`:
```python
# Computes the PP Signal Intelligence score
# Pulls from: article sentiment scores in DB, BTC price API, fear/greed API
# Weights: article 30%, price momentum 25%, onchain 20%, social 15%, fear/greed 10%
# Caches result for 2 minutes
# Returns: {"score": int, "classification": str, "components": dict, "ts": str}
```

### Step 4 — Wire all free API endpoints:
Update routes.py to serve all /api/v2/terminal/* endpoints.
Free endpoints return real data, no auth.
Commander endpoints check for valid API key in Authorization header.
Invalid key → 401. Expired subscription → 402.

### Step 5 — Stripe integration for $29/mo:
Use existing Stripe setup from p3-premium-stripe branch (already merged).
Add new price object: STRIPE_COMMANDER_PRICE_ID (monthly, $29).
Success URL: /terminal?activated=1 (shows welcome banner + API key).
Webhook: subscription.created → user.tier = 'commander' → generate API key.

### Step 6 — "See What You're Missing" mechanic:
Implement exactly as specced above. This is non-negotiable.
5-second preview, gold countdown bar on each panel, re-engagement banner after.

### Step 7 — Mobile responsive:
375px must look intentional. Panels stack. Top bar collapses to just price + live dot.
No horizontal scroll anywhere. Touch targets ≥44px.

### Step 8 — Performance:
All external API calls cached server-side (never expose keys to browser).
Page initial load: no API calls block render. Skeleton loading states in each panel.
After render: fetch all free data, populate panels. Commander data only if authenticated.
Target: First Contentful Paint < 1s.

### Step 9 — Regression + commit:
regression_test.sh → 0 FAILs
git add -A && git commit -m "feat: SESSION 1 — Pulse Terminal world-class rebuild, free/commander tiers, Signal Intelligence, $29/mo Stripe" && git push

### Quality bar — before committing, verify:
- [ ] Every panel renders with real data (no "—" or "N/A" on any field)
- [ ] Locked panels show real blurred data (not placeholder)
- [ ] "See What You're Missing" mechanic works and re-locks after 5s
- [ ] Stripe checkout opens for $29/mo plan
- [ ] API key generated on successful subscription
- [ ] Mobile 375px: no horizontal scroll, panels stack cleanly
- [ ] Top status bar stays fixed on scroll
- [ ] BTC price flashes on update
- [ ] All timestamps show "X min ago" format and update in real time
- [ ] Lighthouse mobile score ≥ 88

---

## WHAT SUCCESS LOOKS LIKE

A free user lands on /terminal and within 10 seconds:
1. Sees BTC price, mempool, fear & greed — beautiful, live, actually useful
2. Sees 4-6 locked panels with real data blurred behind them
3. Sees "PP SIGNAL: ?? / 100 — BULLISH" almost readable behind a lock
4. Clicks "SEE WHAT YOU'RE MISSING" out of curiosity
5. Watches all panels unlock for 5 seconds
6. Reads "MVRV: 2.14 — ACCUMULATE" and "SIGNAL: 74 — BULLISH" in crystal clarity
7. Panels re-lock
8. Reads: "You just saw Commander access for 5 seconds. Never lose that again. → $29/MO"
9. Reaches for card.

That is the funnel. Build it.
