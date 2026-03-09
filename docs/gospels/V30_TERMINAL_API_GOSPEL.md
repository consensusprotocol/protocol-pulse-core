# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
# ------------------------------------------------------------

# PROTOCOL PULSE — GOSPEL: V30 PULSE TERMINAL API
# Branch: feature/v30-terminal-api | Created: 2026-03-09
---

## WHAT THIS IS
Pulse Terminal is the monetization engine. It exposes Protocol Pulse's intelligence
data as a paid API. Three tiers: Watcher ($19/mo), Commander ($49/mo), Sovereign ($99/mo).
Commander is the priority — ship it first.

## THE LAWS

### LAW 1: Commander tier ($49/mo) ships first — this is the only tier for launch
- Watcher and Sovereign tiers are specced but NOT BUILT in this session
- Commander endpoints first, others added in V31

### LAW 2: API auth via API keys (not JWT, not OAuth)
- Keys stored in api_keys table with usage tracking
- Format: `pp_cmd_{32 random chars}` for Commander
- Rate limit: 1000 req/day for Commander
- Auth header: `X-PP-API-Key: pp_cmd_xxxxx`

### LAW 3: Five Commander endpoints
```
GET /api/v2/terminal/topics          ← top topics last 24hr (from articles)
GET /api/v2/terminal/entities        ← named entities + sentiment
GET /api/v2/terminal/sentiment       ← BTC sentiment score 0-100
GET /api/v2/terminal/breaking        ← breaking articles (last 2hr, score > 80)
GET /api/v2/terminal/network         ← live network stats (hashrate, difficulty, nodes)
```

### LAW 4: Stripe integration for Commander
- Stripe webhook: payment_intent.succeeded → create api_key → email to subscriber
- /api/v2/terminal/subscribe → Stripe Checkout session
- STRIPE_SECRET_KEY in .env

### LAW 5: Response format (consistent across all endpoints)
```json
{
    "tier": "commander",
    "endpoint": "topics",
    "timestamp": "2026-03-09T12:00:00Z",
    "cache_age_seconds": 45,
    "data": {...},
    "rate_limit": {
        "requests_today": 42,
        "limit": 1000,
        "resets_at": "2026-03-10T00:00:00Z"
    }
}
```

## DATABASE
```sql
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT UNIQUE NOT NULL,    -- SHA256 of actual key (never store plaintext)
    key_prefix TEXT NOT NULL,         -- first 8 chars for display
    tier TEXT NOT NULL DEFAULT 'commander',
    subscriber_email TEXT NOT NULL,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    requests_today INTEGER DEFAULT 0,
    requests_total INTEGER DEFAULT 0,
    last_used_at DATETIME,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_prefix TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    response_ms INTEGER,
    status_code INTEGER,
    ip_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## ENDPOINT IMPLEMENTATIONS
```python
@app.route('/api/v2/terminal/topics')
@require_terminal_auth('commander')
@cache.cached(timeout=300)
def terminal_topics():
    topics = Article.query.filter(
        Article.published == True,
        Article.created_at > datetime.utcnow() - timedelta(hours=24)
    ).with_entities(Article.category, func.count(Article.id)).group_by(Article.category)\
     .order_by(func.count(Article.id).desc()).limit(20).all()
    return terminal_response('topics', [{'topic': t[0], 'count': t[1]} for t in topics])

@app.route('/api/v2/terminal/sentiment')
@require_terminal_auth('commander')
@cache.cached(timeout=180)
def terminal_sentiment():
    # Aggregate sentiment from recent articles
    # Return score 0-100 (0=bearish, 50=neutral, 100=bullish)
    ...
```

## VERIFICATION
- [ ] POST /api/v2/terminal/subscribe creates Stripe checkout session
- [ ] Stripe webhook creates api_key on payment success
- [ ] GET /api/v2/terminal/topics with valid key returns 200
- [ ] GET /api/v2/terminal/topics with invalid key returns 401
- [ ] Rate limit enforced: 1001st request returns 429
- [ ] /terminal landing page with pricing table exists
- [ ] regression_test.sh: zero FAILs

## CLAUDE CODE PROMPT
```
Read ~/protocol_pulse/docs/gospels/V30_TERMINAL_API_GOSPEL.md.
Branch: feature/v30-terminal-api.
pip install stripe --break-system-packages
1. Create DB migrations: api_keys + api_usage_log
2. Create auth decorator: require_terminal_auth(tier)
3. Implement all 5 Commander endpoints with caching
4. Add rate limiting middleware (reset daily at 00:00 UTC)
5. Stripe webhook handler (payment success → create key → email)
6. Create /api/v2/terminal/subscribe (Stripe checkout)
7. Create /terminal landing page with Commander pricing
8. Test full flow: subscribe → get key → hit endpoints → rate limit
9. regression_test.sh: zero FAILs → commit + push feature/v30-terminal-api
```

## LLM TRIFECTA
### Claude: RISK — key_hash must use SHA256, never store raw keys. Email delivery via Resend.
### Gemini: "Is Flask-Caching appropriate here or should we use Redis for rate limiting?"
### Grok: "Current Stripe API version? Any breaking changes in webhooks for 2026?"

