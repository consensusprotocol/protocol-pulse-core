# PROTOCOL PULSE INTEL DASHBOARD — MULTI-LLM ARCHITECTURE AUDIT
## Premium Subscriber Intelligence Terminal v1.0 — Pre-Build Spec

**Prepared for:** Gemini 2.5 Pro + ChatGPT-4o forensic review  
**Author:** Claude (Anthropic) — initial architecture  
**Date:** March 2026  
**Audit type:** Full-stack architecture review before implementation  

---

## EXECUTIVE BRIEF

Protocol Pulse is an autonomous Bitcoin intelligence and media platform. We are building a **premium subscriber dashboard** — a Bloomberg Terminal / WSJ Markets equivalent for the Bitcoin-native audience. Target subscriber: high-conviction Bitcoin holders, mining operators, family offices, and institutional scouts who need real-time signal aggregation, proprietary sentiment intelligence, and on-chain behavioral analytics in one authenticated dashboard.

This document defines the complete architecture for multi-LLM review. The goal: identify every weakness, gap, and over-engineering risk BEFORE writing a single line of production code.

---

## EXISTING INFRASTRUCTURE (already built — do not duplicate)

### Database (PostgreSQL on Replit)

**Signal collection:**
- `collected_signal` — platform, author_handle, author_tier (verified/legendary/standard), content, sentiment (bullish/bearish/neutral), sentiment_score (float), engagement_likes/reposts/replies, engagement_score, is_verified, is_legendary, posted_at
- `sentiment_snapshot` — score (0-100), state (5 states), velocity, top_keywords JSON, sample_size, verified_weight, computed_at (running every 30 min)
- `sentiment_buffer` — raw staging table
- `intelligence_post` — processed intelligence items
- `kol_pulse_item` — key opinion leader activity

**On-chain / market data:**
- `whale_transaction` — txid, btc_amount, usd_value, fee_sats, block_height, detected_at, is_mega
- `mining_snapshot` — location_id, location_name, overall_score, political_score, economic_score, operational_score, factors_json

**User / auth:**
- `user` table with: subscription_tier (varchar), stripe_customer_id, stripe_subscription_id, subscription_expires_at, mega_whale_email_alerts
- `user_profile`, `user_segment` — behavioral segmentation exists but unused
- `engagement_event`, `page_view` — user behavior tracking tables exist

**Content:**
- `articles` — 40+ columns including sentiment_score, engagement_score, premium_tier, views_count, shares_count

### Existing Frontend
- `IntelTerminal` JS class — sentiment dial with 5 states: CRITICAL_CONTENTION, FRAGMENTED_SIGNAL, EQUILIBRIUM, CONSENSUS_FORMING, ABSOLUTE_SINGULARITY
- `intel_terminal.js` — polling feed at 30s/60s/45s intervals
- `sovereign_gravity_well.js` — exists (unknown current functionality)
- Terminal-style UI partially built

### Current Sentiment Algorithm (BASELINE — being replaced)
Currently: `score = sum(sentiment_scores) / count` — pure average, equal weight to all signals.
`verified_weight` = count of verified authors only (no actual differential weighting).
**Problem: A single legendary Bitcoin thought leader's signal is weighted identically to a random anonymous account. This is the core weakness.**

---

## THE SENTINEL ALGORITHM — PROPRIETARY SENTIMENT WEIGHTING

This is the core IP of the dashboard. Not commodity data. Our moat.

### Multi-Factor Signal Weight Formula

Every `collected_signal` receives a composite weight W before entering the sentiment calculation:

```
W(signal) = W_author × W_recency × W_engagement × W_topic × W_momentum
```

#### W_author — Source Authority Weight
```
legendary (is_legendary=True):  3.5x
verified (is_verified=True):     2.0x  
standard unverified:             1.0x
anonymous/unknown:               0.4x
```
Legendary = Michael Saylor, Cynthia Lummis, Adam Back tier accounts — manually curated list.

#### W_recency — Time Decay
Exponential decay: newer signals carry more weight.
```
W_recency = exp(-λ × age_hours)
λ = 0.12   (half-life ~5.8 hours — aggressive decay for fast markets)
```
Signal from 1 hour ago: 0.887x  
Signal from 6 hours ago: 0.487x  
Signal from 24 hours ago: 0.057x  

#### W_engagement — Social Proof Weight
Normalized engagement relative to author's historical baseline:
```
raw_engagement = likes + (reposts × 3) + (replies × 1.5)
baseline = author's 30-day median engagement
W_engagement = log(1 + raw_engagement / max(baseline, 1)) / log(10)
cap: 2.5x max (prevent viral outliers from dominating)
```

#### W_topic — Bitcoin Relevance Filter
Topic classifier assigns relevance score:
```
PRICE / MACRO / REGULATION:    1.0x (highest signal)
MINING / HASHRATE / ENERGY:    0.9x
ADOPTION / INSTITUTIONAL:      0.85x
TECHNICAL / PROTOCOL:          0.8x
GENERAL BITCOIN:               0.75x
TANGENTIAL (altcoins, etc.):   0.3x
```

#### W_momentum — Cluster Amplification
If 3+ signals with same sentiment appear within 30-minute window from different verified accounts, apply momentum multiplier:
```
cluster_size = count of same-direction verified signals in 30min window
W_momentum = 1.0 + (cluster_size - 2) × 0.15   (cap at 1.75x)
```
This detects genuine coordinated conviction vs. bot amplification.

### Composite Sentinel Score Calculation

```python
def compute_sentinel_score(signals: list[Signal]) -> SentinelScore:
    weighted_bullish = 0
    weighted_bearish = 0
    total_weight = 0
    
    for sig in signals:
        w = (W_author(sig) * W_recency(sig) * W_engagement(sig) * 
             W_topic(sig) * W_momentum(sig, signals))
        
        if sig.sentiment == 'bullish':
            weighted_bullish += sig.sentiment_score * w
        elif sig.sentiment == 'bearish':
            weighted_bearish += abs(sig.sentiment_score) * w
        
        total_weight += w
    
    if total_weight == 0:
        return SentinelScore(score=50, state='EQUILIBRIUM', velocity=0)
    
    # Score: 0 (max bearish) to 100 (max bullish)
    raw_score = 50 + ((weighted_bullish - weighted_bearish) / total_weight) * 50
    score = max(0, min(100, raw_score))
    
    # Velocity: rate of change vs 4-hour prior window
    velocity = score - prior_4h_score
    
    return SentinelScore(score=score, state=classify_state(score), velocity=velocity)
```

### 5 Sentinel States (preserved from existing system, but now threshold-driven)
```
CRITICAL_CONTENTION:    score 0–25     (deep bearish — panic/capitulation)
FRAGMENTED_SIGNAL:      score 26–42    (bearish divergence — uncertainty)
EQUILIBRIUM:            score 43–57    (neutral — sideways)
CONSENSUS_FORMING:      score 58–74    (bullish alignment — conviction building)
ABSOLUTE_SINGULARITY:   score 75–100   (euphoric conviction — potential top signal)
```

### New: Velocity State Layer
Velocity (score change per 4h) adds a second dimension:
```
velocity > +15:  ACCELERATING BULLISH
velocity > +5:   BUILDING
velocity -5–+5:  STABLE
velocity < -5:   DETERIORATING
velocity < -15:  ACCELERATING BEARISH
```
Display: state + velocity = "CONSENSUS_FORMING · ACCELERATING" — actionable.

---

## BEHAVIORAL ANALYTICS ENGINE

### User Behavior Tracking (what we measure)

Every authenticated premium user action gets logged to `engagement_event`:
```
event_type: article_view | signal_click | whale_alert_view | 
            dashboard_session | sentiment_state_change_view |
            mining_intel_view | chart_interaction | alert_triggered
entity_id: relevant item ID
duration_seconds: session/dwell time
metadata_json: additional context
```

### Behavioral Segments (auto-computed nightly)

Segment users into 4 archetypes based on usage pattern:
```
MACRO_WATCHER:     High article dwell time, sentiment state views, low whale/mining
SIGNAL_TRADER:     High whale alert views, short session, high frequency returns
MINING_OPERATOR:   High mining intel dwell, low sentiment, high location_filter usage
STACK_ACCUMULATOR: Low frequency but long sessions, high article completion rate
```

Segment drives: default dashboard layout, alert defaults, content priority, Oracle question suggestions.

### Predictive Churn Score
Weekly computed per user:
```python
churn_risk = f(
    days_since_last_login,      # weight: 0.35
    session_frequency_trend,    # weight: 0.25 (declining = risk)
    alert_engagement_rate,      # weight: 0.20 (ignoring alerts = risk)
    content_completion_rate,    # weight: 0.20
)
```
High churn risk → trigger retention campaign, personalized Oracle briefing, push notification.

---

## DASHBOARD ARCHITECTURE — FULL STACK

### Premium Tier Gate

**Tiers:**
```
free:       Basic feed, 24h delayed sentiment score, 3 articles/day
signal:     $29/mo — Real-time sentinel score, whale alerts, 7-day history
intel:      $79/mo — Full dashboard, mining intel, behavioral analytics, Oracle chat
sovereign:  $299/mo — All intel + API access, custom alerts, white-glove onboarding
```

**Auth enforcement (Flask middleware):**
```python
def require_tier(min_tier: str):
    TIER_RANK = {'free': 0, 'signal': 1, 'intel': 2, 'sovereign': 3}
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect('/login?next=' + request.path)
            user_tier = current_user.subscription_tier or 'free'
            if TIER_RANK.get(user_tier, 0) < TIER_RANK.get(min_tier, 0):
                # Check if subscription is still valid
                if current_user.subscription_expires_at < datetime.utcnow():
                    current_user.subscription_tier = 'free'
                    db.session.commit()
                return jsonify({'error': 'upgrade_required', 'min_tier': min_tier}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

### Backend API Routes (new Flask blueprint: `routes_intel_dashboard.py`)

```
GET  /intel/dashboard              — Main dashboard HTML (requires: intel)
GET  /intel/api/sentinel           — Current Sentinel score + state + velocity (signal+)
GET  /intel/api/sentinel/history   — 7-day score history, 1h buckets (signal+)
GET  /intel/api/signals            — Live signal feed, paginated (signal+)
GET  /intel/api/signals/breakdown  — Bullish/bearish breakdown by author tier (intel+)
GET  /intel/api/whales             — Recent whale transactions + mega alerts (signal+)
GET  /intel/api/whales/pattern     — 7d whale accumulation vs distribution ratio (intel+)
GET  /intel/api/mining             — Mining intelligence by location (intel+)
GET  /intel/api/behavioral/me      — Current user's segment + usage stats (intel+)
GET  /intel/api/behavioral/cohort  — Cohort comparison (intel+)
GET  /intel/api/leaderboard        — Top signal contributors (signal+)
POST /intel/api/alerts/configure   — Set custom alert thresholds (intel+)
GET  /intel/api/export             — Data export CSV/JSON (sovereign+)
WS   /intel/ws/live                — WebSocket for real-time updates (signal+)
```

### Sentinel Recompute Service (scheduler)

```python
# Runs every 5 minutes (upgrade from current 30-min cadence)
# New: separate fast-path (5min) for verified/legendary signals only
# Full computation (all signals) every 30 min unchanged

def recompute_sentinel_fast():
    """5-minute fast path: verified + legendary signals only, last 2 hours"""
    signals = CollectedSignal.query.filter(
        CollectedSignal.is_verified == True,
        CollectedSignal.posted_at >= datetime.utcnow() - timedelta(hours=2)
    ).all()
    score = compute_sentinel_score(signals)
    db.session.add(SentinelFastSnapshot(score=score, computed_at=datetime.utcnow()))
    db.session.commit()
    # Push to WebSocket subscribers
    socketio.emit('sentinel_update', score.to_dict(), room='premium')
```

---

## FRONTEND — BLOOMBERG TERMINAL AESTHETIC

### Layout: 6-Panel Dashboard Grid

```
┌─────────────────────────────────────────────────────────┐
│  PROTOCOL PULSE INTEL  ·  [tier badge]  ·  [Oracle btn] │
├──────────────┬──────────────┬──────────────────────────────┤
│   SENTINEL   │  WHALE FLOW  │     SIGNAL FEED             │
│  Score: 62.4 │  +12,450 BTC │  @Saylor: "Every dip..."   │
│  CONSENSUS   │  7d: ACCUM.  │  @Brunell: "Hashrate at..." │
│  ↑ BUILDING  │  Mega: 3     │  @Dashjr: "Ordinals..."    │
├──────────────┴──────────────┤                             │
│    SENTINEL HISTORY         │  [more signals...]          │
│  [72h sparkline chart]      │                             │
│  [velocity bands]           ├──────────────────────────────┤
├─────────────────────────────┤   MINING INTEL              │
│    SIGNAL BREAKDOWN         │  US:   ████ 8.4             │
│  ▓▓▓▓▓▓▓▓░░ 68% Bullish    │  TX:   ███░ 7.1             │
│  Legendary:  ██ 2 signals   │  KY:   ██░░ 5.8             │
│  Verified:   ████ 12        │  [location map]             │
│  Standard:   ████████ 45    └──────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
```

### Key UI Components

**Sentinel Dial** (existing, enhanced):
- Current: static SVG dial
- New: animated canvas-based gauge with live updating
- Add: velocity arrow overlaid on dial (pointing direction of movement)
- Add: historical ghost line (where score was 4h ago)
- Color zones: red (0-25) → yellow (26-42) → white (43-57) → orange (58-74) → Bitcoin gold (75-100)

**Whale Flow Panel:**
- Real-time feed of transactions >100 BTC
- Net flow calculation: accumulation (exchange outflows) vs distribution (exchange inflows)
- 7-day net flow sparkline
- Mega whale alerts (is_mega=True) with push notification badge

**Signal Feed:**
- Chronological with author tier badges (👑 legendary, ✓ verified)
- Sentiment color coding (green/red/gray)
- Composite weight displayed as signal strength bar
- Filter: all / bullish only / bearish only / legendary only

**Sentinel History Chart:**
- 72-hour score timeline (D3.js or Chart.js)
- Shaded state zones in background
- Velocity bands as color gradient overlay
- Key event annotations (Bitcoin price crossings, news items from articles table)

**Mining Intel Panel:**
- Location cards with political/economic/operational subscores
- Color-coded overall score
- Trend indicator (improving/declining vs prior snapshot)

**Behavioral Insights Panel (intel+ only):**
- User's archetype badge (MACRO_WATCHER etc.)
- Personalized metrics: "You read 87% of CONSENSUS_FORMING articles to completion"
- Smart alert suggestion: "Based on your behavior, you may want: Mega Whale alerts ON"

---

## REAL-TIME INFRASTRUCTURE — WEBSOCKET LAYER

Currently: polling every 30-60s. Target: real-time push for premium subscribers.

```python
# Flask-SocketIO rooms by tier
# On connect: join room based on subscription_tier
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        tier = current_user.subscription_tier or 'free'
        join_room(tier)
        join_room('premium' if tier in ['signal','intel','sovereign'] else 'free')
        emit('connected', {'tier': tier, 'sentinel': get_current_sentinel()})

# Events pushed to rooms:
# 'sentinel_update'  → all premium rooms (every 5min fast path)
# 'whale_alert'      → signal+ rooms (on whale_transaction insert)
# 'mega_whale_alert' → intel+ rooms (is_mega=True only)
# 'signal_burst'     → intel+ rooms (cluster detection trigger)
# 'state_change'     → all premium rooms (when Sentinel state changes)
```

---

## STRIPE INTEGRATION — WHAT'S MISSING

The DB has `stripe_customer_id`, `stripe_subscription_id`, `subscription_expires_at` — but no webhook handler exists.

Missing pieces:
1. **`/stripe/webhook`** endpoint — handle subscription.created, subscription.deleted, invoice.payment_failed, customer.subscription.updated
2. **Checkout session creation** — `/premium/upgrade` POST → Stripe Checkout → redirect
3. **Portal link** — `/premium/manage` → Stripe Customer Portal
4. **Grace period logic** — on payment_failed: 3-day grace, then downgrade to free

---

## DATA PIPELINE — WHAT NEEDS TO BE BUILT

### New DB tables needed:

```sql
-- Sentinel weighted score (fast path)
CREATE TABLE sentinel_fast_snapshot (
    id SERIAL PRIMARY KEY,
    score FLOAT NOT NULL,
    state VARCHAR(40),
    velocity FLOAT,
    verified_only BOOLEAN DEFAULT TRUE,
    sample_size INT,
    computed_at TIMESTAMP DEFAULT NOW()
);

-- Per-signal composite weight (audit trail)
CREATE TABLE signal_weight_log (
    id SERIAL PRIMARY KEY,
    signal_id INT REFERENCES collected_signal(id),
    w_author FLOAT,
    w_recency FLOAT,
    w_engagement FLOAT,
    w_topic FLOAT,
    w_momentum FLOAT,
    composite_weight FLOAT,
    computed_at TIMESTAMP DEFAULT NOW()
);

-- User behavioral events (granular)
CREATE TABLE intel_event (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES "user"(id),
    event_type VARCHAR(50),
    entity_type VARCHAR(30),
    entity_id INT,
    duration_seconds INT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Whale flow aggregates (pre-computed)
CREATE TABLE whale_flow_daily (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE,
    total_inflow_btc FLOAT,
    total_outflow_btc FLOAT,
    net_flow_btc FLOAT,
    mega_count INT,
    computed_at TIMESTAMP DEFAULT NOW()
);

-- Custom user alerts
CREATE TABLE user_alert_config (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES "user"(id),
    alert_type VARCHAR(40),
    threshold_value FLOAT,
    direction VARCHAR(10),  -- above | below | change
    push_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## WHAT WSJ / BLOOMBERG DO THAT WE MUST MATCH

| Feature | WSJ Markets | Bloomberg Terminal | Protocol Pulse Intel |
|---|---|---|---|
| Real-time price feed | ✓ | ✓ | via existing APIs |
| Sentiment score | ✓ (AAII survey) | ✓ (MLIV pulse) | ✓ Sentinel (proprietary) |
| Institutional flow data | ✓ | ✓ | ✓ Whale transactions |
| Expert opinion weighting | ✗ | ✓ | ✓ Legendary/Verified tiers |
| Predictive behavioral model | ✗ | partial | ✓ Archetype segmentation |
| Real-time push alerts | ✓ | ✓ | ✓ WebSocket (new) |
| Historical backtesting | ✓ | ✓ | Phase 2 |
| API access | ✓ ($) | ✓ ($$$$) | ✓ Sovereign tier |
| Mobile | ✓ | limited | ✓ responsive |
| AI-powered brief | ✗ | ✗ | ✓ Oracle integration |

**Our unique advantages Bloomberg doesn't have:**
1. Real-time social signal weighting by Bitcoin-specific authority tiers
2. AI Oracle voice brief tied to live sentiment
3. Mining geopolitical intelligence (political/economic/operational scoring)
4. Cypherpunk/sovereignty framing — cultural fit that Bloomberg explicitly lacks

---

## IMPLEMENTATION PHASES

### Phase 0 — Foundation (1 session, ~4 hours)
- Sentinel Algorithm service (`services/sentinel_engine.py`)
- New DB tables migration
- `routes_intel_dashboard.py` blueprint with all API endpoints
- Stripe webhook handler
- Subscription gate middleware

### Phase 1 — Core Dashboard (1 session, ~6 hours)
- Dashboard HTML template (`templates/intel_dashboard.html`)
- Sentinel dial canvas component
- Signal feed component
- Whale flow panel
- Basic chart (sentinel history, 72h)

### Phase 2 — Real-time Layer (1 session, ~4 hours)
- Flask-SocketIO integration
- WebSocket room management
- Live sentinel push (fast path recompute)
- Whale alert push

### Phase 3 — Behavioral Analytics (1 session, ~4 hours)
- `intel_event` logging middleware
- Behavioral archetype classifier
- Churn score computation
- Personalized dashboard layout by archetype

### Phase 4 — Premium Conversion (1 session, ~3 hours)
- Stripe checkout + portal
- Upgrade prompts (blurred/locked content for free tier)
- Onboarding flow for new intel subscribers
- Email alert pipeline

---

## QUESTIONS FOR MULTI-LLM REVIEW

1. **Algorithm correctness:** Is the Sentinel multi-factor weighting formula sound? Any mathematical edge cases (division by zero, score overflow, degenerate inputs)?

2. **Gaming resistance:** Can bad actors manipulate the Sentinel score? How would you harden W_engagement and W_momentum against coordinated inauthentic behavior?

3. **Latency vs accuracy tradeoff:** The 5-minute fast path vs 30-minute full computation — is this the right split? What's the risk of the fast path diverging significantly from the full score?

4. **Behavioral archetype classifier:** Are 4 archetypes the right granularity? Are the feature weights for churn prediction defensible?

5. **WebSocket scalability:** Flask-SocketIO with gevent vs eventlet — which for Replit's constraints? What happens at 500 concurrent premium subscribers?

6. **Stripe webhook security:** What are the critical failure modes in the subscription lifecycle handler?

7. **Missing data sources:** What real-time Bitcoin data feeds should we add that we haven't listed? (mempool fee rates, exchange order book depth, ETF flow data, MVRV-Z score equivalent?)

8. **Dashboard UX:** Is the 6-panel layout the right default? What would Bloomberg's UX team change?

9. **Moat assessment:** Is the Sentinel algorithm genuinely defensible IP, or can competitors replicate it trivially?

10. **Phase priority:** Given Protocol Pulse's stage (early premium rollout), what is the highest-leverage single thing to ship first?

---

## SUCCESS METRICS

**Technical:**
- Sentinel recompute latency < 500ms for fast path
- WebSocket push latency < 200ms from signal ingestion to dashboard update
- Dashboard load time < 1.5s (all panels)
- Zero data leakage between tiers

**Product:**
- 100 intel subscribers within 60 days of launch
- NPS > 40 at 30-day mark
- Churn < 8% monthly at intel tier
- Average session duration > 8 minutes (Bloomberg benchmark: 14 min)

**Revenue:**
- Signal tier ($29): target 200 subscribers = $5,800 MRR
- Intel tier ($79): target 100 subscribers = $7,900 MRR
- Sovereign tier ($299): target 10 subscribers = $2,990 MRR
- **Target MRR at 90 days: $16,690**

---

*End of audit spec. Submit to Gemini 2.5 Pro and ChatGPT-4o for independent forensic review before implementation.*
