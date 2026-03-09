# PHASE 0 ADDENDUM — P3 Premium Stripe
# Created: 2026-03-09
# Top synthesis suggestions and HOW they'll be implemented

## P0 ADDITIONS (implementing all)

### 1. Entitlements System (not just tier strings)
**HOW**: Add `entitlements` JSON column to `ApiSubscriber` table. Feature flags stored as
JSON dict (e.g., `{"stream": true, "webhook": true, "signal": true}`). `api_key_service.py`
checks entitlements per request. Demo tier gets limited subset. Enables future plan versioning
without schema migration.

### 2. Sliding Window Rate Limiting (not just hourly resets)
**HOW**: `api_request_log` already logs per-request with timestamps. Rate limiter queries
COUNT(requests WHERE created_at > now()-1hr) — true sliding window. Also adds burst allowance:
Commander gets 1200 requests/hour but max 50/minute burst. Graceful degradation: 429 response
includes `Retry-After` header computed from oldest request in window.

### 3. WebSocket Real-Time Feed
**HOW**: SSE stream at `/api/v2/terminal/stream` for Commander tier (as spec). Full WebSocket
is blocked by our Flask stack without gevent/eventlet. SSE with reconnect logic is the
production-safe choice for the existing Flask app. Client-side auto-reconnect at 3s interval.
Channel parameter: `?channel=breaking|sentiment|all`. This delivers the real-time experience
without WebSocket server complexity.

### 4. Scoped API Keys with Expiry
**HOW**: `ApiSubscriber` gets `key_scopes` TEXT column (JSON array: `["read", "stream", "webhook"]`)
and `key_expires_at` DATETIME column (NULL = no expiry). Key creation sets scopes based on tier.
Key rotation: `POST /api/dashboard/rotate-key` generates new key, deactivates old (with 1hr grace).

### 5. Advanced Developer Onboarding
**HOW**:
- Demo key auto-provisioned on app startup (tier="demo", rate_limit=20/hr)
- `/api/playground` shows language-specific code snippets (Python, curl, Node.js) that auto-fill
  with the demo key. Tabs for each language.
- After checkout success: email includes quickstart code snippet + link to playground with their key

### 6. Usage Analytics Dashboard
**HOW**: `/api/dashboard` shows 24-hour sparkline (12 data points, 2hr buckets) from
`api_request_log`. Uses vanilla JS `<canvas>` for sparkline rendering — no Chart.js dependency.
Endpoint breakdown pie chart (text-based percentages — no external lib).

## P1 ADDITIONS (implementing as time allows)

### 7. Webhook Delivery System
**HOW**: Background thread (`threading.Thread`) checks `api_subscribers` where `webhook_url IS NOT NULL`
every 60s. On new breaking article: POST to webhook_url signed with HMAC-SHA256. 3 retry attempts
with exponential backoff. Log all delivery attempts.

### 8. Billing Portal Link
**HOW**: `POST /api/dashboard/billing-portal` creates Stripe Customer Portal session, redirects
subscriber. Requires STRIPE_SECRET_KEY. Degrades gracefully (shows email to contact) if key not set.

## ARCHITECTURE DECISIONS

- **SQLite for api_subscribers**: Same DB as rest of app. `api_request_log` gets indexed on
  `(api_key, created_at)` per spec. No separate DB needed.
- **No Flask-SocketIO**: SSE is sufficient for breaking news stream. Avoids server complexity.
- **Resend for welcome email**: Already in .env. Falls back gracefully if key missing.
- **premium.html upgrade**: Add Commander API tier card between existing Commander and Sovereign.
  Keep existing tiers intact — don't break existing subscription flow.
- **Separate Blueprint**: `routes_premium_api.py` as a Blueprint, imported in app.py.
  Keeps routes.py clean. Consistent with routes_api_v2.py pattern.

## WHAT WE DO NOT BUILD (keeping scope clean)
- Team/Workspace management — P1 but too complex for this session; documented as future work
- Predictive analytics ML — needs separate ML infrastructure
- Edge CDN — infrastructure, not app-level
- JWT tokens — overkill for our scale; UUID4 prefix keys are sufficient
