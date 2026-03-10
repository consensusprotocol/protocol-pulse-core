# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.

# PROTOCOL PULSE — GOSPEL: P3 PREMIUM + STRIPE
# Branch: feature/p3-premium-stripe | Created: 2026-03-09

---

## WHAT THIS IS
Commander tier ($49/month). Stripe Checkout. API key issuance. Terminal API endpoints
gated behind auth. Self-service portal. API Playground. Usage analytics.
The monetization foundation for Protocol Pulse.

## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY)
Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-premium-stripe --phase0
Ask all 3 LLMs: "What are the most advanced 2026 developer API monetization features?
How do the best API-first companies (Stripe, Twilio, OpenAI) handle onboarding,
billing, rate limiting, and developer experience in 2026?"
Incorporate top P0 ideas before building.

## THE LAWS
### LAW 1: Stripe keys come from .env — never hardcode
STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_COMMANDER_PRICE_ID must be in .env
After building, print a clear SETUP.md with exact steps for PBX to:
1. Create Stripe account + get test keys
2. Create Commander product ($49/mo recurring) in Stripe dashboard
3. Add all 3 keys to .env on Ultron
4. Test with Stripe test mode first

### LAW 2: API keys are UUID4 — never sequential, never guessable
import uuid; api_key = "pp_cmd_" + str(uuid.uuid4()).replace("-", "")
Example: pp_cmd_a3f9b2c1d4e5f6a7b8c9d0e1f2a3b4c5
Rate limit: 1000 requests/hour per key. Track in api_subscribers table.

### LAW 3: Webhook validation is non-negotiable
Always: stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
If validation fails: return 400 immediately, log the attempt
Handle: payment_intent.succeeded, customer.subscription.deleted, invoice.payment_failed

### LAW 4: API Playground is sandboxed — uses a demo key
Create a read-only demo api_key (tier="demo") that returns sample data
Playground hits the actual endpoints with this key — real experience, safe data
Rate limit demo key: 20 req/hour to prevent abuse

## ARCHITECTURE

### Database Schema
```sql
CREATE TABLE IF NOT EXISTS api_subscribers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  api_key TEXT UNIQUE NOT NULL,       -- "pp_cmd_" + uuid4
  tier TEXT DEFAULT "commander",      -- commander|enterprise|demo
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  stripe_price_id TEXT,
  requests_this_hour INTEGER DEFAULT 0,
  requests_today INTEGER DEFAULT 0,
  requests_total INTEGER DEFAULT 0,
  rate_limit_per_hour INTEGER DEFAULT 1000,
  webhook_url TEXT,                   -- optional: subscriber can receive pushes
  webhook_secret TEXT,                -- HMAC secret for their webhook
  is_active INTEGER DEFAULT 1,
  subscription_status TEXT DEFAULT "active", -- active|past_due|canceled
  current_period_end DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_used_at DATETIME
);

CREATE TABLE IF NOT EXISTS api_request_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  api_key TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  response_time_ms INTEGER,
  status_code INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Index for rate limiting:
CREATE INDEX IF NOT EXISTS idx_api_log_key_time ON api_request_log(api_key, created_at);
```

### Services
```
services/stripe_service.py       — checkout, webhook, subscription management
services/api_key_service.py      — auth middleware, rate limiting, usage tracking
services/terminal_api_service.py — the actual data endpoints for subscribers
```

### Terminal API Endpoints (all require X-API-Key header)
```python
GET /api/v2/terminal/topics      → top 20 topics from last 24h articles
GET /api/v2/terminal/entities    → named entities: people, orgs, coins
GET /api/v2/terminal/sentiment   → aggregate sentiment + components
GET /api/v2/terminal/breaking    → articles published last 2hrs
GET /api/v2/terminal/signal      → composite Signal Strength 0-100
GET /api/v2/terminal/status      → subscriber usage stats + quota
GET /api/v2/terminal/stream      → SSE stream of breaking news (Commander only)
```

Each endpoint:
- Validates X-API-Key → 401 if invalid
- Checks hourly rate limit → 429 if exceeded with Retry-After header
- Logs request to api_request_log
- Returns JSON with: data, meta {requests_this_hour, requests_remaining, tier}

### Stripe Flow
POST /api/v2/terminal/subscribe → create_checkout_session(email) → redirect to Stripe
GET /subscribe/success?session_id=... → validate → show api_key → send welcome email
POST /webhook/stripe → handle payment events → create/deactivate api_keys
GET /api/dashboard → subscriber self-service (their key + usage + billing portal link)

### Premium Landing Page (/premium — upgrade existing template)
3 tiers as glassmorphism cards:
FREE: Articles, daily brief, basic charts (current state)
COMMANDER ($49/mo): Terminal API (1000 req/hr), breaking news stream,
  entity tracking, sentiment data, signal strength, SSE stream
  "JOIN THE INTEL FEED →" button — red, animated pulse border on hover
ENTERPRISE: Contact (custom volume, webhook delivery, white-label)

### API Playground (/api/playground)
Interactive page — try the API before subscribing:
- Dropdown: select endpoint to test
- Click "RUN" → hits endpoint with demo key → shows formatted JSON response
- Shows response time, rate limit headers
- "Get Full Access →" CTA at bottom
- Syntax highlighted JSON output (Prism.js from cdnjs)

### Usage Analytics Dashboard (/api/dashboard — requires subscriber login or api_key)
- Your API key (masked, reveal button)
- Requests today / this month / total
- Hourly usage sparkline (last 24hrs)
- Subscription status + next billing date
- "Manage Billing" → Stripe Customer Portal link
- Webhook configuration (optional: enter URL + secret to receive push events)

### Webhook Delivery (optional feature for subscribers)
When new breaking article published: POST to subscriber's webhook_url
Payload: {event: "breaking_article", data: {title, summary, url, published_at}}
Sign with HMAC-SHA256 using their webhook_secret → X-PP-Signature header
Queue delivery, retry 3x on failure, log all attempts

## SETUP.md — Generate this file with exact PBX instructions
After building, create ~/protocol_pulse/STRIPE_SETUP.md:
```
# STRIPE SETUP FOR PBX
1. Go to https://dashboard.stripe.com → create account if needed
2. Go to Products → Create: "Protocol Pulse Commander" $49/mo recurring
3. Copy the Price ID (starts with price_...)
4. Go to Developers → API keys → copy Secret key (sk_test_... for testing)
5. Go to Developers → Webhooks → Add endpoint:
   URL: https://protocolpulse.io/webhook/stripe
   Events: payment_intent.succeeded, customer.subscription.deleted, invoice.payment_failed
   Copy Signing Secret (whsec_...)
6. SSH to Ultron: add to ~/protocol_pulse/.env:
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_COMMANDER_PRICE_ID=price_...
7. Restart Flask: tmux send-keys -t flask_main "C-c" && tmux send-keys -t flask_main "..." Enter
8. Test with Stripe test card: 4242 4242 4242 4242, any future date, any CVC
```

## VERIFICATION
- [ ] GET /premium → HTTP 200, 3-tier display
- [ ] POST /api/v2/terminal/subscribe → redirects to Stripe (requires STRIPE key in .env)
- [ ] GET /api/v2/terminal/topics with valid api_key → 200 with real data
- [ ] GET /api/v2/terminal/topics with bad key → 401
- [ ] 1001st request → 429 with Retry-After header
- [ ] Stripe webhook processes payment_intent.succeeded → creates api_key in DB
- [ ] Welcome email sent via Resend on subscription
- [ ] GET /api/playground → playground renders, demo key works
- [ ] STRIPE_SETUP.md exists with complete instructions
- [ ] regression_test.sh: zero FAILs
- [ ] git commit + push to origin feature/p3-premium-stripe
