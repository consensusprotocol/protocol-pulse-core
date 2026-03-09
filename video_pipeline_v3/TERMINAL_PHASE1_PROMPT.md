Read ~/protocol_pulse/PULSE_TERMINAL_LAWS.md completely first. This is the product bible.
Also read PIPELINE_LAWS.md and ~/protocol_pulse/CONTENT_INTELLIGENCE_LAWS.md.

You are building PULSE TERMINAL PHASE 1 — the foundation of a premium Bloomberg-for-Bitcoin intelligence product.

=== TASK 1: REPLACE MOCK DATA WITH REAL READS (routes_api_terminal.py) ===

The current Terminal API returns hardcoded mock data. Replace with real reads from the daemon's output files.

Data files written by the channel daemon:
  data/intelligence/daily_signals.json — topic velocity
  data/intelligence/entity_mentions.json — entity tracking (may not exist yet)
  data/intelligence/sentiment.json — market sentiment (may not exist yet)

Check what files actually exist:
  ls -la data/intelligence/

For each endpoint:
1. GET /api/v2/terminal/topics — Read daily_signals.json, format per PULSE_TERMINAL_LAWS Section 3
   Include: topic name, velocity_score, channels_covering, channel_names, sentiment, trend
   Add query params: ?period=24h, ?min_velocity=50, ?topic=mining
   If file doesn't exist, return {"data": null, "error": "Intelligence data not yet available. Daemon populating.", "meta": {"freshness": null}}

2. GET /api/v2/terminal/entities — Read entity_mentions.json
   If file doesn't exist yet, generate it from the archive:
   Parse all transcripts in data/channel_archive/*/. json
   Simple NER: search for known entities (Saylor, BlackRock, Fidelity, Grayscale, etc.)
   Count mentions per entity per 24h window
   Write to data/intelligence/entity_mentions.json
   Build utils/entity_tracker.py for this

3. GET /api/v2/terminal/sentiment — Read sentiment.json
   If file doesn't exist, compute from daily_signals:
   Average sentiment scores across all topics
   Classify: <40 bearish, 40-60 neutral, >60 bullish
   Write to data/intelligence/sentiment.json
   Build utils/sentiment_calculator.py for this

4. GET /api/v2/terminal/breaking — Read daily_signals for any topic with velocity >= 4 channels in 3 hours
   Return breaking=true/false with alert details

5. GET /api/v2/terminal/network — NEW endpoint
   Call Bitnodes API (or read from node_monitor cache):
   from utils.node_monitor import get_node_snapshot
   Return: total_nodes, net_change_24h, countries
   Also add: BTC price from existing /api/v2/prices endpoint
   Halving countdown: compute from current block height

Add response metadata to ALL endpoints:
  "meta": {
    "tier": "free|operator|commander|sovereign",
    "freshness": "2026-03-05T15:45:00Z",
    "rate_limit_remaining": 987,
    "rate_limit_reset": "2026-03-06T00:00:00Z"
  }

Commit: git add routes_api_terminal.py utils/entity_tracker.py utils/sentiment_calculator.py -m 'feat: Terminal API Phase 1 — real data reads, entity tracker, sentiment calculator'

=== TASK 2: RATE LIMITING + API KEY MANAGEMENT ===

Build proper rate limiting per tier:

config/api_keys.json:
{
  "keys": [
    {"key": "pp-test-commander-001", "tier": "commander", "subscriber": "PBX Test", "created": "2026-03-05", "active": true},
    {"key": "pp-free-demo-001", "tier": "free", "subscriber": "Demo", "created": "2026-03-05", "active": true}
  ]
}

Rate limits per tier:
  free: 10 requests/day, topics endpoint only (top 3), 24h data delay
  operator: 100 requests/day, all endpoints, real-time
  commander: 1000 requests/day, all endpoints, real-time, WebSocket access
  sovereign: unlimited, all endpoints, real-time, WebSocket, custom queries

Implement in routes_api_terminal.py:
  - Decorator: @require_api_key that checks X-API-Key header
  - Load api_keys.json, validate key, determine tier
  - Track usage in data/terminal/usage/{api_key_hash}.json (daily counters)
  - Return 401 for invalid key, 429 for exceeded limit with Retry-After header
  - Free tier: filter topics to top 3, add 24h delay to timestamps

Commit: git add routes_api_terminal.py config/api_keys.json -m 'feat: Terminal API key auth + tier-based rate limiting'

=== TASK 3: OPENAPI/SWAGGER DOCUMENTATION ===

Create a Swagger/OpenAPI spec for the Terminal API:

Build static/terminal_api_docs.html OR use flask-swagger-ui:
  pip install flask-swagger-ui (if available on Ultron, else build static HTML)

Create openapi_terminal.yaml:
  openapi: 3.0.3
  info:
    title: Protocol Pulse Terminal API
    version: 1.0.0
    description: Premium Bitcoin Intelligence — Bloomberg for Bitcoin
  servers:
    - url: https://protocolpulse.replit.app/api/v2/terminal
  security:
    - ApiKeyAuth: []
  paths:
    /topics: ...
    /entities: ...
    /sentiment: ...
    /breaking: ...
    /network: ...

Each endpoint fully documented with:
  - Description
  - Parameters (query params)
  - Response schema with examples
  - Error responses (401, 429)

Serve at: /api/v2/terminal/docs

Commit: git add openapi_terminal.yaml static/ -m 'feat: Terminal API OpenAPI docs'

=== TASK 4: STRIPE SUBSCRIPTION WIRING ===

Check what Stripe integration already exists on Replit:
  Search Replit codebase: grep -rn 'stripe\|STRIPE' /home/runner/workspace/ 2>/dev/null | head -20

If Stripe is already configured:
  - Create Products: "Pulse Terminal Operator" ($19/mo), "Pulse Terminal Commander" ($49/mo), "Pulse Terminal Sovereign" ($99/mo)
  - Create checkout session endpoint: POST /api/v2/terminal/subscribe
    Body: {"tier": "commander", "email": "user@example.com"}
    Returns: Stripe checkout URL
  - Webhook endpoint: POST /api/v2/terminal/webhook
    Handles: checkout.session.completed → generate API key, store in api_keys.json
    Handles: customer.subscription.deleted → deactivate API key
  - API key delivery: After successful payment, email API key via Resend

If Stripe is NOT configured:
  - Create the endpoint stubs with TODO comments
  - Document what Stripe keys are needed (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET)
  - Build the subscription flow logic so it's ready to wire when keys are added

Commit: git add -m 'feat: Terminal Stripe subscription flow'

=== TASK 5: PUSH TO REPLIT ===

The Terminal API needs to be live on Replit (public-facing server).
Push routes_api_terminal.py to Replit via relay:
  1. Read the file content
  2. Push via Replit relay exec endpoint
  3. Verify the blueprint is registered in app.py
  4. Test: curl https://protocolpulse.replit.app/api/v2/terminal/topics -H "X-API-Key: pp-test-commander-001"

Also push: config/api_keys.json, openapi_terminal.yaml

Commit on Ultron: git add -A && git push origin main

After ALL tasks: Report which endpoints are live, test each with curl, confirm rate limiting works.