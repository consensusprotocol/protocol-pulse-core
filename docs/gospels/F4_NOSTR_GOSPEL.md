# PROTOCOL PULSE — GOSPEL: F4 NOSTR INTELLIGENCE SYSTEM
# Status: GOSPEL. Load into EVERY Claude Code session touching Nostr.
# Branch: feature/f4-nostr
# Created: 2026-03-09

---

## WHAT THIS FEATURE IS

Nostr is the censorship-resistant social protocol that Bitcoin's cypherpunk
community has adopted. Protocol Pulse monitors Nostr for Bitcoin signal,
scores content by engagement and quality, surfaces the best content on the
platform, and publishes Protocol Pulse's own content to Nostr automatically.

Two deliverables:
1. **nostr_monitor.py** — backend service that connects to Nostr relays,
   subscribes to Bitcoin topics, scores content, stores in DB
2. **/nostr onboarding page** — public-facing page explaining Nostr +
   showing live top Nostr content from our monitor

---

## THE LAWS

### LAW 1: Engagement scoring formula is fixed
```
ENGAGEMENT_SCORE = (
    zaps * 10 +        # Bitcoin payments = strongest signal
    quotes * 5 +       # Quoted reposts = editorial endorsement
    reposts * 3 +      # Simple reposts = amplification
    replies * 2 +      # Conversation = engagement
    reactions * 1      # Likes/reactions = passive appreciation
)
```

### LAW 2: Approved relay list (use all 4, failover gracefully)
```python
NOSTR_RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.nostr.band",
    "wss://relay.primal.net"
]
```
If a relay disconnects, reconnect with exponential backoff (1s, 2s, 4s, max 60s).
Never crash on relay disconnect.

### LAW 3: Bitcoin signal filter — only track relevant content
Subscribe to NIP-01 events with these filter criteria:
```json
{"kinds": [1, 30023], "#t": ["bitcoin", "btc", "lightning", "nostr", "sovereignty"]}
```
Also monitor specific high-signal pubkeys (seed list — update as community grows).

### LAW 4: nostr_monitor.py runs as asyncio, not threads
- Single event loop, websockets library for relay connections
- 4 concurrent websocket connections (one per relay)
- Event deduplication by event ID before scoring
- Max queue depth: 1000 events in memory — flush to DB every 60s

### LAW 5: Protocol Pulse publishes to Nostr
- Every new article published on PP → auto-post to Nostr (NIP-23 long-form)
- Every daily video published → auto-post to Nostr (NIP-1 short note with link)
- PP Nostr identity: generate keypair once, store in .env as NOSTR_PRIVATE_KEY
- DO NOT post more than 10 times per day from PP account (avoid spam reputation)

---

## ARCHITECTURE

### File Map
```
~/protocol_pulse/
├── core/
│   ├── services/
│   │   └── nostr_service.py      ← relay manager, event processor
│   └── routes.py                 ← /nostr + /api/nostr/* routes
├── nostr/
│   ├── nostr_monitor.py          ← asyncio service (run as daemon)
│   ├── nostr_publisher.py        ← publish PP content to Nostr
│   └── nostr_keys.py             ← keypair management
├── templates/
│   └── nostr.html                ← Nostr onboarding + live feed page
└── cron/
    └── nostr_cron.py             ← hourly top-content refresh
```

### Event Processing Pipeline
```
Relay websocket → receive event JSON
  → validate NIP-01 structure (id, pubkey, kind, content, sig)
  → check dedup cache (event ID seen before?)
  → score_event(event) → engagement_score
  → extract_entities(event) → {bitcoin_keywords, npubs_mentioned}
  → store in nostr_events table
  → update nostr_top_content cache
```

---

## DATABASE

```sql
CREATE TABLE IF NOT EXISTS nostr_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,          -- Nostr event ID (32-byte hex)
    pubkey TEXT NOT NULL,                   -- Author pubkey
    kind INTEGER NOT NULL,                  -- 1=note, 30023=long-form
    content TEXT NOT NULL,
    engagement_score REAL DEFAULT 0,
    zaps INTEGER DEFAULT 0,
    quotes INTEGER DEFAULT 0,
    reposts INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    reactions INTEGER DEFAULT 0,
    bitcoin_relevance REAL DEFAULT 0,       -- 0-1 float
    relay_source TEXT,
    created_at INTEGER NOT NULL,            -- Nostr timestamp (unix)
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_nostr_score ON nostr_events(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_nostr_created ON nostr_events(created_at DESC);

CREATE TABLE IF NOT EXISTS nostr_tracked_pubkeys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pubkey TEXT UNIQUE NOT NULL,
    display_name TEXT,
    nip05 TEXT,                             -- verified Nostr address
    follower_tier TEXT DEFAULT 'standard', -- 'vip', 'standard'
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## NOSTR ONBOARDING PAGE SPEC (/nostr)

### Purpose
- Explain what Nostr is (for Bitcoin newcomers)
- Show Protocol Pulse's Nostr feed (live top content)
- CTA: "Follow Protocol Pulse on Nostr" (QR code + npub)
- Show top 10 Nostr posts from our monitor (refresh every 5 min)

### Layout
```
┌───────────────────────────────────────────────┐
│  ⚡ NOSTR INTELLIGENCE                         │
│  Censorship-resistant Bitcoin signal          │
├───────────────────────────────────────────────┤
│  WHAT IS NOSTR?                               │
│  [3-sentence explainer]                       │
│  [Follow PP: QR code + npub address]          │
├───────────────────────────────────────────────┤
│  TOP SIGNAL RIGHT NOW                        │
│  [Top 10 Nostr posts by engagement score]    │
│  [Each: author, content preview, score, time]│
│  [Auto-refresh every 5 min]                  │
├───────────────────────────────────────────────┤
│  RELAY STATUS                                 │
│  relay.damus.io     [●] CONNECTED            │
│  nos.lol            [●] CONNECTED            │
│  relay.nostr.band   [○] DISCONNECTED         │
│  relay.primal.net   [●] CONNECTED            │
└───────────────────────────────────────────────┘
```

---

## API ENDPOINTS

```python
@app.route('/nostr')
def nostr_page():
    top_content = nostr_service.get_top_content(limit=10)
    relay_status = nostr_service.get_relay_status()
    pp_npub = current_app.config['NOSTR_NPUB']
    return render_template('nostr.html', ...)

@app.route('/api/nostr/top')
def nostr_top():
    # GET → [{event_id, pubkey, content, score, created_at}] top 10

@app.route('/api/nostr/relay-status')
def nostr_relay_status():
    # GET → [{relay, connected, last_event_at, events_today}]

@app.route('/api/nostr/publish', methods=['POST'])
@require_admin
def nostr_publish():
    # POST {content, kind} → publish to all relays
```

---

## NOSTR PUBLISHER (for PP content)

```python
# nostr_publisher.py
def publish_article(article):
    """NIP-23 long-form note"""
    event = {
        "kind": 30023,
        "tags": [
            ["title", article.title],
            ["t", "bitcoin"],
            ["t", "protocolpulse"],
        ],
        "content": article.content_markdown,
        "created_at": int(time.time())
    }
    sign_and_publish(event)

def publish_video(video_title, video_url):
    """NIP-1 short note"""
    event = {
        "kind": 1,
        "tags": [["t", "bitcoin"], ["t", "video"]],
        "content": f"New Pulse Check: {video_title}\n\n{video_url}",
        "created_at": int(time.time())
    }
    sign_and_publish(event)
```

---

## KEYPAIR SETUP

```python
# On first run, generate keypair and store in .env
# NOSTR_PRIVATE_KEY=<32-byte hex>
# NOSTR_PUBLIC_KEY=<32-byte hex>  (derived)
# NOSTR_NPUB=<bech32 npub...>     (for display)
```

---

## VERIFICATION CRITERIA

- [ ] nostr_monitor.py starts without error, connects to ≥3 relays
- [ ] Events flow into nostr_events table within 60s of start
- [ ] /nostr page returns HTTP 200 with relay status visible
- [ ] /api/nostr/top returns 10 events with scores
- [ ] PP keypair generated and NOSTR_NPUB in .env
- [ ] Manual publish test: POST /api/nostr/publish succeeds
- [ ] regression_test.sh: zero FAILs

---

## CLAUDE CODE PROMPT

```
Read ~/protocol_pulse/docs/gospels/F4_NOSTR_GOSPEL.md (THIS FILE).

Branch: feature/f4-nostr (create from main).

First: pip install websockets pynostr secp256k1 --break-system-packages

BUILD:
1. Create nostr/nostr_keys.py (keypair generation + bech32 encoding)
2. Generate PP keypair, add to .env as NOSTR_PRIVATE_KEY + NOSTR_PUBLIC_KEY
3. Create nostr/nostr_monitor.py (asyncio, 4 relay connections, event processing)
4. Create nostr/nostr_publisher.py (sign_and_publish, publish_article, publish_video)
5. Create core/services/nostr_service.py (DB interface, top content, relay status)
6. DB migration: nostr_events + nostr_tracked_pubkeys tables
7. Seed 10 high-signal Bitcoin Nostr pubkeys (Jack Dorsey, Fiatjaf, etc.)
8. Create templates/nostr.html per gospel spec
9. Add /nostr + /api/nostr/* routes to core/routes.py
10. Start nostr_monitor in background tmux session: tmux new -s nostr_monitor
11. Verify events flowing after 60s
12. Manual publish test
13. regression_test.sh: zero FAILs
14. git commit + push to feature/f4-nostr
```

---

## LLM TRIFECTA AUDIT NOTES

### Claude Gap Analysis:
- RISK: websockets reconnection logic is critical — must never crash daemon
- RISK: NIP-01 event signing requires secp256k1 — verify library works on Ubuntu 24
- MISSING: Content moderation filter (Nostr has no censorship — some content will be bad)
- MISSING: Bitcoin relevance scoring (not all "bitcoin" tagged content is high quality)
- IMPORTANT: pynostr vs python-nostr — verify which package is current/maintained

### For Gemini: "Review asyncio + websockets architecture for 4 concurrent relay connections."
### For Grok: "Current Nostr relay list — are all 4 relays still active? Best free Python Nostr library 2026?"
