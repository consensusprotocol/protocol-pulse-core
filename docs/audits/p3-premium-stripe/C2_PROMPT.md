# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: p3-premium-stripe
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE REVIEW REPORT: p3-premium-stripe Feature

#### SECTION 1: CORRECTNESS
Walking through the main user flow for the Stripe integration and API subscription system:

1. **User Flow Step-by-Step**:
   - **Subscription Initiation**: User navigates to `/premium`, enters email, and initiates checkout via `/api/v2/terminal/subscribe` (routes_premium_api.py:459-506). The endpoint creates a Stripe Checkout session and redirects to Stripe.
   - **Payment Completion**: After payment, Stripe redirects to `/subscribe/terminal/success` (routes_premium_api.py:509-550), which attempts to retrieve the API key or provisions it if not yet created.
   - **Webhook Handling**: Stripe sends a webhook to `/webhook/stripe/terminal` (routes_premium_api.py:553-625) to confirm subscription (`checkout.session.completed`), update status (`customer.subscription.updated`), or cancel (`customer.subscription.deleted`).
   - **API Usage**: User accesses endpoints like `/api/v2/terminal/topics` (routes_premium_api.py:283-287) with their API key, subject to rate limiting and entitlement checks (api_key_service.py:173-253).
   - **Dashboard & Management**: User manages their subscription at `/api/dashboard` (routes_premium_api.py:631-665), rotates keys, or configures webhooks.

2. **Logic Errors & Silent Failures**:
   - **Silent Webhook Delay**: In `terminal_subscribe_success` (routes_premium_api.py:509-550), if the webhook hasn't fired yet, the API key might not be available. The code attempts to provision it (line 535), but if this fails silently, the user sees no key and no clear error message beyond a generic one (line 541). This could confuse users.
   - **Rate Limit Calculation**: In `check_rate_limit` (api_key_service.py:100-141), the sliding window for hourly rate limiting is correctly implemented, but the burst check (lines 126-134) uses a fixed 60-second window without considering the actual minute alignment, potentially leading to inconsistent burst limits across minute boundaries.
   - **Email Sending Race**: Welcome email sending is offloaded to a background thread (routes_premium_api.py:581-585), but there's no retry mechanism or logging if it fails after the webhook response is sent. This could silently fail to notify users.

3. **Race Conditions**:
   - **Webhook vs. Success Page**: There's a potential race between the webhook handler (`terminal_stripe_webhook`, routes_premium_api.py:553-625) creating the `ApiSubscriber` and the success page (`terminal_subscribe_success`, lines 509-550) trying to retrieve it. If the webhook is delayed, the success page might provision a duplicate (line 535), though it checks for an existing subscriber first, mitigating this somewhat.
   - **Rate Limit Updates**: The `ApiSubscriber` table tracks `requests_this_hour` (models.py:955), but updates are not atomic with request logging in `log_request` (api_key_service.py:144-170). Concurrent requests could undercount usage, though the sliding window in `check_rate_limit` (lines 107-111) mitigates this by querying logs directly.

4. **N+1 Query Problems**:
   - **No Obvious N+1**: API endpoints like `terminal_topics` (routes_premium_api.py:283-287) fetch data in bulk (e.g., `_get_topics_data`, lines 125-155) without loops over DB rows triggering additional queries. Rate limiting in `check_rate_limit` (api_key_service.py:107-111) uses a single COUNT query, which is efficient.

5. **Edge Cases**:
   - **Empty DB**: Functions like `_get_topics_data` (routes_premium_api.py:125-155) handle empty article results by returning fallback data (line 154), which is good. However, if `ApiSubscriber` is empty or demo key provisioning fails (app.py:157-160), the playground (`/api/playground`, routes_premium_api.py:771-776) might not work as expected without a fallback.
   - **API Timeout**: External API calls to ElevenLabs (tts_engine.py:212-223) have a 90-second timeout, but Stripe calls (routes_premium_api.py:489-502) lack explicit timeouts, risking hanging requests if Stripe is slow.
   - **Bad Input**: Email validation in `/api/v2/terminal/subscribe` (routes_premium_api.py:467-471) is rudimentary (`@` check), allowing invalid emails to reach Stripe, which might reject them later without clear user feedback.

#### SECTION 2: LAW COMPLIANCE
- **LAW 1: Stripe keys come from .env — never hardcode**
  - **COMPLIANT**: Stripe keys are sourced from environment variables in `routes_premium_api.py:474-479` and `stripe_service.py:12-13`. `STRIPE_SETUP.md` (lines 42-48) provides clear instructions for setting up `.env` on Ultron, and steps for obtaining test keys and creating a Commander product are detailed (lines 6-20).
- **LAW 2: API keys are UUID4 — never sequential, never guessable**
  - **COMPLIANT**: API keys are generated using UUID4 with a prefix in `api_key_service.py:77-81` (e.g., `pp_cmd_<uuid>`). Rate limiting is implemented with a sliding window of 1000 requests/hour for Commander tier (api_key_service.py:27-30), tracked via `api_request_log` table (mo

## GEMINI — CYCLE 1 OUTPUT
This is a forensic code review of the `p3-premium-stripe` feature.

### SECTION 1: CORRECTNESS
The code is largely correct and implements the core user flow as intended. A user can subscribe via Stripe, receive an API key, and use it against the protected endpoints. However, there are several correctness issues:

*   **Logic Errors:**
    *   `core/templates/api_dashboard.html:161`: The dashboard displays a "Requests Today" metric (`subscriber.requests_today`), but this value is never calculated or updated in the backend. The `ApiSubscriber` model has the column, but it remains at its default of 0. The rate limiting is hourly, so this metric is both unimplemented and potentially confusing to the user.
    *   `core/services/stripe_service.py:34-115`: The functions `handle_checkout_completed` and `handle_subscription_deleted` are written to operate on the `User` model, which is incorrect for the standalone `ApiSubscriber` flow. While they don't appear to be called by the new webhook handler, their presence is misleading and dangerous, as they could be hooked up by mistake in the future. They represent dead, incorrect code.

*   **N+1 Query Problems:**
    *   `core/services/api_key_service.py:304-311`: The `get_hourly_usage_sparkline` function executes 24 separate database queries inside a `for` loop to generate the 24-hour usage data. This is a classic N+1 query problem. This should be a single, more efficient query using `GROUP BY`.

*   **Specification Mismatch:**
    *   `core/routes_premium_api.py:681`: The `PHASE0_ADDENDUM.md` specifies a 1-hour grace period for rotated keys. The implementation at `rotate_api_key` invalidates the old key immediately. While the user is correctly informed of this, it does not match the architectural decision document.

### SECTION 2: LAW COMPLIANCE
*   **LAW 1: Stripe keys come from .env:** **COMPLIANT.** The code consistently uses `os.environ.get()` to fetch Stripe keys. The `STRIPE_SETUP.md` file provides clear instructions for populating the `.env` file.

*   **LAW 2: API keys are UUID4:** **COMPLIANT.** `core/services/api_key_service.py:81` uses `uuid.uuid4()` to generate keys with the correct prefix. The rate limiting system is implemented and tracks requests in the `api_request_log` table.

*   **LAW 3: Webhook validation is non-negotiable:** **VIOLATION.**
    *   `core/routes_premium_api.py:559-560`: The webhook handler includes the logic: `if not webhook_secret: logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature validation")`. This explicitly bypasses the non-negotiable security control if the environment variable is missing, allowing an attacker to forge any webhook event (e.g., creating free premium accounts) simply by sending a POST request. This is a critical vulnerability. The code should return a 400 or 500 error immediately if the secret is not configured.

*   **LAW 4: API Playground is sandboxed:** **COMPLIANT.** The playground at `/api/playground` is correctly provisioned with a hardcoded, read-only demo key (`pp_demo_...`). The key's rate limit (20 req/hour) is enforced by the same rate-limiting logic as paid keys.

### SECTION 3: SECURITY
*   **Authentication Bypasses:**
    *   `core/routes_premium_api.py:559-560`: The most severe issue is the webhook signature validation bypass described in LAW 3. An attacker can craft a fake `checkout.session.completed` event to provision themselves a free, permanent Commander API key.

*   **Unvalidated User Input:**
    *   The application seems to use the SQLAlchemy ORM correctly, which mitigates SQL injection risks. User input like email is used in `filter_by` which is safe. Other inputs (API keys, webhook URLs) are handled appropriately.

*   **Secrets in Code:**
    *   No hardcoded Stripe secrets were found. The use of `os.environ.get()` is consistent. The demo key is hardcoded but is documented as a public, rate-limited key, which is acceptable.

### SECTION 4: FRONTEND QUALITY
The frontend work is of high quality.

*   **Layout & Functionality:** The new UI elements in `premium.html` and the new `api_dashboard.html` and `api_playground.html` pages are well-designed, responsive, and match the site's existing aesthetic. They look professional, not like a prototype.
*   **Async States:** All asynchronous JavaScript operations (e.g., creating a checkout session, rotating a key, running a playground request) correctly handle loading, success, and error states, providing clear feedback to the user. This is excellent.
*   **Bugs:** The only notable issue is the display of the incorrect "Requests Today" metric on the dashboard, as mentioned in the Correctness section.

### SECTION 5: BACKEND QUALITY
The backend quality is generally high, with a few areas for improvement.

*   **DB Operations:** Most database writes within the webhook handler and dashboard routes are wrapped in `try/except` blocks with `db.session.rollback()` on failure. This is good practice.
*   **External API Calls:** Calls to R

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main flow walkthrough

#### 1. User opens `/premium`
The Terminal API upsell UI is present in `core/templates/premium.html:320-369`. It presents `$49/mo`, email input, and checkout CTA.

**Issues**
- The feature spec says “Add Commander API tier card between existing Commander and Sovereign,” but this implementation adds a separate hero/section above the pricing grid, not a pricing card in-grid (`premium.html:320-369`, `PHASE0_ADDENDUM.md:60-61`). That’s not a correctness bug, but it diverges from the stated implementation.
- The page claims accepted payment methods include Bitcoin/Lightning (`premium.html:483-491`), but this feature only implements Stripe card checkout for the API tier. That is misleading product behavior.

#### 2. User submits email to `/api/v2/terminal/subscribe`
Route is in `core/routes_premium_api.py:459-506`.

What works:
- Validates email superficially (`470-471`)
- Reads Stripe secret and price ID from env (`473-485`)
- Creates Stripe Checkout session (`487-501`)

**Issues**
- No CSRF protection on this POST route. Since it creates billable checkout sessions, this should at least be origin-checked or CSRF-protected.
- Email validation is too weak (`470-471`); malformed addresses pass if they contain `@`.
- No idempotency key passed to Stripe. Repeated clicks / retries can create multiple checkout sessions.
- No timeout/retry wrapper around Stripe API call.
- Success URL assumes webhook or immediate provisioning will succeed, but the success page has racey fallback behavior.

#### 3. Stripe redirects to `/subscribe/terminal/success`
Route is `core/routes_premium_api.py:508-550`.

What works:
- Retrieves session from Stripe if `session_id` exists (`516-525`)
- Looks up subscriber by email (`529-533`)
- If missing, tries to provision directly from checkout session (`534-538`)

**Major correctness issue**
- `provision_terminal_subscriber()` only provisions when `metadata["subscription_type"] == "terminal_api"` (`core/services/stripe_service.py:134-136`).
- In Stripe webhooks, metadata on `checkout.session.completed` is available because it was set on the Checkout Session (`routes_premium_api.py:496-500`).
- But on the success page, `stripe.checkout.Session.retrieve(..., expand=["customer"])` may not reliably include all fields needed for downstream provisioning of subscription/customer state, and more importantly this path duplicates webhook provisioning logic. It can race with the webhook and create inconsistent behavior.
- If webhook fires after success-page fallback provisioning, it will hit the existing subscriber path and reuse the same key, which is okay. But the design is brittle and duplicates side effects.

**Another issue**
- Welcome email can be sent twice:
  - once from success page fallback (`538`)
  - once from webhook thread (`579-584`)

#### 4. Stripe webhook hits `/webhook/stripe/terminal`
Route is `core/routes_premium_api.py:552-626`.

What works:
- Reads raw payload and signature header (`555-557`)
- Calls `validate_webhook_signature()` when secret exists (`565-569`)
- Handles:
  - `checkout.session.completed` (`577-584`)
  - `customer.subscription.deleted` (`586-589`)
  - `customer.subscription.updated` (`589-607`)
  - `invoice.payment_failed` (`608-620`)

**Major correctness/security issue**
- If `STRIPE_WEBHOOK_SECRET` is missing, the code **accepts unsigned webhook payloads** and parses raw JSON (`559-565`). That is a direct violation of LAW 3 and a production-critical security flaw.

**Spec mismatch**
- LAW 3 requires handling `payment_intent.succeeded`, `customer.subscription.deleted`, `invoice.payment_failed`.
- This code does **not** handle `payment_intent.succeeded`.
- `STRIPE_SETUP.md` tells PBX to subscribe to `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`, `invoice.payment_failed` (`32-35`), which also diverges from the law.

#### 5. Subscriber provisioning
Implemented in `core/services/stripe_service.py:117-190`.

What works:
- Creates or reactivates `ApiSubscriber`
- Generates API key via `generate_api_key()`
- Stores entitlements and scopes

**Issues**
- `stripe_price_id` field exists in model (`models.py:952`) but is never populated.
- `current_period_end` exists in model (`975`) but is never populated.
- Existing subscriber reactivation path does not update `rate_limit_per_hour` (`151-158`), so a demo or prior enterprise/commander subscriber could retain stale limits.
- Existing subscriber reactivation path always sets scopes to `["read", "stream", "webhook"]` (`157`) even if tier should differ.
- New subscriber path hardcodes `rate_limit_per_hour=1000 if tier == "commander" else -1` (`171`) instead of using centralized tier config.
- Unused imports `uuid` and `generate_webhook_secret` in this function.

#### 6. API key auth and rate limiting
Implemented in `core/services/api_key_service.py`.

What works:
- Looks up subscriber by API key (`192-193`)
- Checks `is_key_valid()

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — P3-PREMIUM-STRIPE — CYCLE 1
Generated: 2026-03-09 14:25
Models: grok, gemini, gpt4o

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok  | Consensus |
|------------------|--------|--------|-------|-----------|
| Backend Logic    | 75     | 68     | 72    | **72**    |
| Frontend/UI      | 95     | 80     | 85    | **87**    |
| Error Handling   | 85     | 70     | 75    | **77**    |
| Security         | 40     | 35     | 65    | **47**    |
| Performance      | 70     | 55     | 72    | **66**    |
| Law Compliance   | 75     | 60     | 88    | **74**    |
| World-Class Gap  | 65     | 60     | 70    | **65**    |
| **OVERALL**      | **72** | **61** | **75**| **69**    |

> **Scoring notes:** Grok scored security and law compliance significantly higher than Gemini/GPT-4o because it did not flag the webhook bypass as a violation (it marked LAW 3 compliant while the other two models correctly identified the conditional bypass). Grok's score is an outlier on those dimensions and is overruled by the majority. The consensus security score of 47 reflects the critical webhook vulnerability.

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

---

### U1 — Webhook Signature Validation Can Be Bypassed When Secret Is Absent
**File:** `core/routes_premium_api.py:559-565`
**All three models flagged this.** The code path explicitly skips `stripe.Webhook.construct_event()` when `STRIPE_WEBHOOK_SECRET` is not set and falls back to parsing raw JSON. This allows an unauthenticated attacker to POST a crafted `checkout.session.completed` payload and receive a free, permanent Commander API key. This is the single highest-severity issue in the codebase.
**Fix:** If `STRIPE_WEBHOOK_SECRET` is absent, return `HTTP 500` with a log-level CRITICAL alert and abort. Never process unsigned webhook payloads under any condition.

---

### U2 — "Requests Today" Dashboard Metric Is Permanently Zero / Never Populated
**File:** `core/templates/api_dashboard.html:161`, `core/services/api_key_service.py` (no update path), `models.py` (column exists but unused)
**All three models flagged this.** The `ApiSubscriber.requests_today` column is declared in the model but never incremented. The dashboard displays it as a live metric. Users will always see `0`, which is actively misleading.
**Fix:** Either (a) compute it as a real-time COUNT query over `ApiRequestLog` for the current UTC calendar day in the dashboard route and pass it to the template, or (b) remove the metric from the UI entirely until it is implemented. Option (a) is preferred for a world-class product.

---

### U3 — Welcome Email Can Be Sent Twice (Success Page + Webhook Thread)
**File:** `core/routes_premium_api.py:538` (success page fallback provisioning) and `579-584` (webhook handler)
**All three models independently identified this.** If the success page triggers fallback provisioning before the webhook fires, the email is sent once from the success path and

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: PHASE0_ADDENDUM.md (70 lines)
```
   1 | # PHASE 0 ADDENDUM — P3 Premium Stripe
   2 | # Created: 2026-03-09
   3 | # Top synthesis suggestions and HOW they'll be implemented
   4 | 
   5 | ## P0 ADDITIONS (implementing all)
   6 | 
   7 | ### 1. Entitlements System (not just tier strings)
   8 | **HOW**: Add `entitlements` JSON column to `ApiSubscriber` table. Feature flags stored as
   9 | JSON dict (e.g., `{"stream": true, "webhook": true, "signal": true}`). `api_key_service.py`
  10 | checks entitlements per request. Demo tier gets limited subset. Enables future plan versioning
  11 | without schema migration.
  12 | 
  13 | ### 2. Sliding Window Rate Limiting (not just hourly resets)
  14 | **HOW**: `api_request_log` already logs per-request with timestamps. Rate limiter queries
  15 | COUNT(requests WHERE created_at > now()-1hr) — true sliding window. Also adds burst allowance:
  16 | Commander gets 1200 requests/hour but max 50/minute burst. Graceful degradation: 429 response
  17 | includes `Retry-After` header computed from oldest request in window.
  18 | 
  19 | ### 3. WebSocket Real-Time Feed
  20 | **HOW**: SSE stream at `/api/v2/terminal/stream` for Commander tier (as spec). Full WebSocket
  21 | is blocked by our Flask stack without gevent/eventlet. SSE with reconnect logic is the
  22 | production-safe choice for the existing Flask app. Client-side auto-reconnect at 3s interval.
  23 | Channel parameter: `?channel=breaking|sentiment|all`. This delivers the real-time experience
  24 | without WebSocket server complexity.
  25 | 
  26 | ### 4. Scoped API Keys with Expiry
  27 | **HOW**: `ApiSubscriber` gets `key_scopes` TEXT column (JSON array: `["read", "stream", "webhook"]`)
  28 | and `key_expires_at` DATETIME column (NULL = no expiry). Key creation sets scopes based on tier.
  29 | Key rotation: `POST /api/dashboard/rotate-key` generates new key, deactivates old (with 1hr grace).
  30 | 
  31 | ### 5. Advanced Developer Onboarding
  32 | **HOW**:
  33 | - Demo key auto-provisioned on app startup (tier="demo", rate_limit=20/hr)
  34 | - `/api/playground` shows language-specific code snippets (Python, curl, Node.js) that auto-fill
  35 |   with the demo key. Tabs for each language.
  36 | - After checkout success: email includes quickstart code snippet + link to playground with their key
  37 | 
  38 | ### 6. Usage Analytics Dashboard
  39 | **HOW**: `/api/dashboard` shows 24-hour sparkline (12 data points, 2hr buckets) from
  40 | `api_request_log`. Uses vanilla JS `<canvas>` for sparkline rendering — no Chart.js dependency.
  41 | Endpoint breakdown pie chart (text-based percentages — no external lib).
  42 | 
  43 | ## P1 ADDITIONS (implementing as time allows)
  44 | 
  45 | ### 7. Webhook Delivery System
  46 | **HOW**: Background thread (`threading.Thread`) checks `api_subscribers` where `webhook_url IS NOT NULL`
  47 | every 60s. On new breaking article: POST to webhook_url signed with HMAC-SHA256. 3 retry attempts
  48 | with exponential backoff. Log all delivery attempts.
  49 | 
  50 | ### 8. Billing Portal Link
  51 | **HOW**: `POST /api/dashboard/billing-portal` creates Stripe Customer Portal session, redirects
  52 | subscriber. Requires STRIPE_SECRET_KEY. Degrades gracefully (shows email to contact) if key not set.
  53 | 
  54 | ## ARCHITECTURE DECISIONS
  55 | 
  56 | - **SQLite for api_subscribers**: Same DB as rest of app. `api_request_log` gets indexed on
  57 |   `(api_key, created_at)` per spec. No separate DB needed.
  58 | - **No Flask-SocketIO**: SSE is sufficient for breaking news stream. Avoids server complexity.
  59 | - **Resend for welcome email**: Already in .env. Falls back gracefully if key missing.
  60 | - **premium.html upgrade**: Add Commander API tier card between existing Commander and Sovereign.
  61 |   Keep existing tiers intact — don't break existing subscription flow.
  62 | - **Separate Blueprint**: `routes_premium_api.py` as a Blueprint, imported in app.py.
  63 |   Keeps routes.py clean. Consistent with routes_api_v2.py pattern.
  64 | 
  65 | ## WHAT WE DO NOT BUILD (keeping scope clean)
  66 | - Team/Workspace management — P1 but too complex for this session; documented as future work
  67 | - Predictive analytics ML — needs separate ML infrastructure
  68 | - Edge CDN — infrastructure, not app-level
  69 | - JWT tokens — overkill for our scale; UUID4 prefix keys are sufficient
  70 | 
```

### File: STRIPE_SETUP.md (124 lines)
```
   1 | # STRIPE SETUP FOR PBX — Terminal API Commander Tier
   2 | # Created: 2026-03-09
   3 | 
   4 | ---
   5 | 
   6 | ## STEP 1: Create Stripe Account
   7 | - Go to https://dashboard.stripe.com
   8 | - Create account if needed (or log in)
   9 | - Stay in TEST MODE first (toggle in top-left: "Test mode")
  10 | 
  11 | ## STEP 2: Create the Commander Product
  12 | 1. Go to **Products** → **+ Add product**
  13 | 2. Name: `Protocol Pulse Commander API`
  14 | 3. Description: `Terminal API — 1,000 req/hr · SSE Stream · Webhook Delivery`
  15 | 4. Pricing model: **Recurring**
  16 | 5. Amount: **$49.00 USD** per **month**
  17 | 6. Click **Save product**
  18 | 7. On the product page, copy the **Price ID** → starts with `price_...`
  19 |    → This is your `STRIPE_COMMANDER_PRICE_ID`
  20 | 
  21 | ## STEP 3: Get API Keys
  22 | 1. Go to **Developers** → **API keys**
  23 | 2. Copy **Secret key** (starts with `sk_test_...` for test mode)
  24 |    → This is your `STRIPE_SECRET_KEY`
  25 | 3. (Do NOT use the publishable key — only the secret key)
  26 | 
  27 | ## STEP 4: Create Webhook Endpoint
  28 | 1. Go to **Developers** → **Webhooks** → **+ Add endpoint**
  29 | 2. Endpoint URL: `https://protocolpulse.io/webhook/stripe/terminal`
  30 |    (For local testing: use Stripe CLI or ngrok)
  31 | 3. Select events to listen to:
  32 |    - `checkout.session.completed`
  33 |    - `customer.subscription.deleted`
  34 |    - `customer.subscription.updated`
  35 |    - `invoice.payment_failed`
  36 | 4. Click **Add endpoint**
  37 | 5. On the webhook page, click **Reveal** on "Signing secret"
  38 |    → Copy the value starting with `whsec_...`
  39 |    → This is your `STRIPE_WEBHOOK_SECRET`
  40 | 
  41 | ## STEP 5: Add Keys to Ultron .env
  42 | SSH to Ultron and add to `~/protocol_pulse/.env`:
  43 | 
  44 | ```bash
  45 | STRIPE_SECRET_KEY=sk_test_...        # from Step 3
  46 | STRIPE_WEBHOOK_SECRET=whsec_...      # from Step 4
  47 | STRIPE_COMMANDER_PRICE_ID=price_...  # from Step 2
  48 | ```
  49 | 
  50 | ## STEP 6: Restart Flask
  51 | ```bash
  52 | # Find the gunicorn/flask process
  53 | tmux list-sessions
  54 | tmux attach -t flask_main
  55 | 
  56 | # Or restart via systemd if configured:
  57 | sudo systemctl restart protocol-pulse
  58 | ```
  59 | 
  60 | ## STEP 7: Test with Test Card
  61 | 1. Go to https://protocolpulse.io/premium
  62 | 2. Enter your email, click "JOIN THE INTEL FEED →"
  63 | 3. On Stripe checkout page:
  64 |    - Card: `4242 4242 4242 4242`
  65 |    - Expiry: Any future date (e.g., `12/28`)
  66 |    - CVC: Any 3 digits (e.g., `123`)
  67 |    - ZIP: Any 5 digits (e.g., `90210`)
  68 | 4. Click "Subscribe"
  69 | 5. You should be redirected to `/subscribe/terminal/success` with your API key
  70 | 6. Check that welcome email was sent (if RESEND_API_KEY is configured)
  71 | 
  72 | ## STEP 8: Verify API Key Works
  73 | ```bash
  74 | # Replace with your actual key from the success page
  75 | curl https://protocolpulse.io/api/v2/terminal/topics \
  76 |   -H "X-API-Key: pp_cmd_your_key_here"
  77 | ```
  78 | Should return: `{"data": [...], "meta": {"tier": "commander", ...}}`
  79 | 
  80 | ## STEP 9: Go Live (when ready)
  81 | 1. Toggle Stripe dashboard from **Test mode** to **Live mode**
  82 | 2. Repeat Steps 2-4 with live keys (they start with `sk_live_`, `price_live_`, `whsec_live_`)
  83 | 3. Update `.env` on Ultron with live keys
  84 | 4. Restart Flask
  85 | 
  86 | ---
  87 | 
  88 | ## VERIFICATION CHECKLIST
  89 | - [ ] GET /premium → HTTP 200, Terminal API section visible
  90 | - [ ] POST /api/v2/terminal/subscribe → Stripe redirect (with STRIPE keys in .env)
  91 | - [ ] GET /api/v2/terminal/topics with valid api_key → 200 with data
  92 | - [ ] GET /api/v2/terminal/topics with bad key → 401
  93 | - [ ] 21st request with demo key → 429 with Retry-After header
  94 | - [ ] Stripe webhook processes checkout.session.completed → creates api_key in DB
  95 | - [ ] Welcome email sent via Resend on subscription
  96 | - [ ] GET /api/playground → playground renders, demo key works
  97 | - [ ] GET /api/dashboard → unauthenticated state shown
  98 | - [ ] GET /api/dashboard?key=pp_cmd_... → subscriber state shown
  99 | 
 100 | ---
 101 | 
 102 | ## TROUBLESHOOTING
 103 | 
 104 | **"Stripe not configured" error on checkout:**
 105 | → STRIPE_SECRET_KEY not in .env. Add it and restart Flask.
 106 | 
 107 | **Webhook not firing / subscriber not created:**
 108 | → Check webhook endpoint URL is correct.
 109 | → Check STRIPE_WEBHOOK_SECRET matches the whsec_ from Stripe dashboard.
 110 | → Check Flask logs: `tail -f logs/app.log`
 111 | 
 112 | **API key not in success page after checkout:**
 113 | → Webhook may not have fired yet. Wait 30s and go to /api/dashboard.
 114 | → Enter your email in the key lookup to find your key.
 115 | → If still missing, check webhook logs in Stripe dashboard.
 116 | 
 117 | **Demo key not working in playground:**
 118 | → Run: `curl http://localhost:5000/api/v2/terminal/topics -H "X-API-Key: pp_demo_00000000000000000000000000000001"`
 119 | → If 401: demo key not provisioned. Restart Flask to trigger provision_demo_key().
 120 | 
 121 | ---
 122 | 
 123 | *Questions: support@protocolpulse.io*
 124 | 
```

### File: core/app.py (177 lines)
```
   1 | import os
   2 | from pathlib import Path
   3 | from dotenv import load_dotenv
   4 | # Load .env from the same directory as this file (core/) so it works from any cwd
   5 | load_dotenv(Path(__file__).resolve().parent / ".env")
   6 | 
   7 | import logging
   8 | import json
   9 | import random
  10 | from flask import Flask, session
  11 | from flask_sqlalchemy import SQLAlchemy
  12 | from flask_migrate import Migrate
  13 | from sqlalchemy.orm import DeclarativeBase
  14 | from flask_login import LoginManager
  15 | from flask_limiter import Limiter
  16 | from flask_limiter.util import get_remote_address
  17 | try:
  18 |     from flask_caching import Cache
  19 |     _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
  20 | except ImportError:
  21 |     _cache = None
  22 | 
  23 | # Configure logging
  24 | logging.basicConfig(level=logging.DEBUG)
  25 | 
  26 | class Base(DeclarativeBase):
  27 |     pass
  28 | 
  29 | # 1. Initialize DB WITHOUT app first to prevent circular loops
  30 | db = SQLAlchemy(model_class=Base)
  31 | 
  32 | # 2. Create the app instance — use absolute paths so templates/static are always found
  33 | #    whether run as "app:app" from core/ or "core.app:app" from project root
  34 | _core_dir = Path(__file__).resolve().parent
  35 | app = Flask(__name__, template_folder=str(_core_dir / "templates"), static_folder=str(_core_dir / "static"))
  36 | 
  37 | # Security: Uses .env secret, but provides a fallback for local dev
  38 | app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_protocol_pulse_2026")
  39 | 
  40 | # Configure the database
  41 | database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
  42 | if database_url.startswith("sqlite:"):
  43 |     # Ensure UTF-8 support for Bitcoin symbols
  44 |     if "?" not in database_url:
  45 |         database_url += "?charset=utf8mb4"
  46 | 
  47 | app.config["SQLALCHEMY_DATABASE_URI"] = database_url
  48 | app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
  49 |     "pool_recycle": 300,
  50 |     "pool_pre_ping": True,
  51 | }
  52 | 
  53 | # 3. Initialize extensions
  54 | db.init_app(app)
  55 | migrate = Migrate(app, db)
  56 | login_manager = LoginManager()
  57 | login_manager.init_app(app)
  58 | login_manager.login_view = "login"
  59 | 
  60 | limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day"])
  61 | limiter.init_app(app)
  62 | 
  63 | if _cache is not None:
  64 |     _cache.init_app(app)
  65 |     cache = _cache
  66 | else:
  67 |     class _NullCache:
  68 |         def init_app(self, app): pass
  69 |         def cached(self, timeout=None, key_prefix=None):
  70 |             def decorator(f): return f
  71 |             return decorator
  72 |     cache = _NullCache()
  73 | 
  74 | @app.context_processor
  75 | def inject_csrf():
  76 |     """Inject CSRF token for forms. Generate once per session."""
  77 |     if "csrf_token" not in session:
  78 |         session["csrf_token"] = os.urandom(32).hex()
  79 |     return {"csrf_token": session.get("csrf_token")}
  80 | 
  81 | 
  82 | @app.after_request
  83 | def add_static_cache_headers(response):
  84 |     """Allow browsers to cache static assets for 1 day."""
  85 |     from flask import request
  86 |     if request.path.startswith("/static/"):
  87 |         response.cache_control.max_age = 86400
  88 |         response.cache_control.public = True
  89 |     return response
  90 | 
  91 | 
  92 | # 4. Define Template Filters
  93 | @app.template_filter('inject_ads')
  94 | def inject_ads(content):
  95 |     import models
  96 |     try:
  97 |         active_ads = models.Advertisement.query.filter_by(is_active=True).all()
  98 |         if not active_ads:
  99 |             return content
 100 |         ad = random.choice(active_ads)
 101 |         ad_html = f'''
 102 |         <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
 103 |             <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
 104 |             <a href="{ad.target_url}" target="_blank" rel="noopener" class="text-decoration-none">
 105 |                 <img src="{ad.image_url}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{ad.name}">
 106 |                 <p class="mb-0 text-white fw-bold">{ad.name}</p>
 107 |             </a>
 108 |         </div>
 109 |         '''
 110 |         parts = content.split('</p>', 2)
 111 |         if len(parts) > 2:
 112 |             return parts[0] + '</p>' + parts[1] + '</p>' + ad_html + parts[2]
 113 |         return content + ad_html
 114 |     except Exception as e:
 115 |         logging.warning(f"Ad injection failed: {e}")
 116 |         return content
 117 | 
 118 | @app.template_filter('from_json')
 119 | def from_json_filter(value):
 120 |     if not value:
 121 |         return []
 122 |     try:
 123 |         return json.loads(value)
 124 |     except (json.JSONDecodeError, TypeError):
 125 |         return []
 126 | 
 127 | # 5. User loader for Flask-Login
 128 | @login_manager.user_loader
 129 | def load_user(user_id):
 130 |     import models
 131 |     return models.User.query.get(int(user_id))
 132 | 
 133 | # =====================================
 134 | # THE IGNITION ZONE (CRITICAL ORDER)
 135 | # =====================================
 136 | # When we run as python app.py, __name__ is "__main__". Later, "import routes" does
 137 | # "from app import app", which loads this file again as module "app" (a second Flask
 138 | # app). Routes then register on that second app, but we call app.run() on this one → 404.
 139 | # So make "app" resolve to this same module when we are the main script.
 140 | if __name__ == "__main__":
 141 |     import sys
 142 |     sys.modules["app"] = sys.modules["__main__"]
 143 | 
 144 | with app.app_context():
 145 |     # 1. Load the models into memory first
 146 |     import models
 147 |     # 2. Create the tables (migration-safe: adds new columns/tables without dropping existing)
 148 |     db.create_all()
 149 |     # 3. ONLY NOW load the routes
 150 |     import routes
 151 |     # 4. Register Terminal API blueprint
 152 |     try:
 153 |         from routes_premium_api import premium_api
 154 |         app.register_blueprint(premium_api)
 155 |         logging.info("Terminal API blueprint registered")
 156 |         # 5. Provision demo API key for playground
 157 |         from services.api_key_service import provision_demo_key
 158 |         provision_demo_key(db, models)
 159 |     except Exception as e:
 160 |         logging.warning("Terminal API blueprint not loaded: %s", e)
 161 | 
 162 | # Diagnose: confirm / and /debug-routes are registered (debug 404)
 163 | try:
 164 |     rules = [r.rule for r in app.url_map.iter_rules()]
 165 |     has_root = "/" in rules
 166 |     logging.info("Routes registered: %s ... (/) present: %s", len(rules), has_root)
 167 |     if not has_root:
 168 |         logging.warning("Missing '/' route! Sample rules: %s", rules[:20])
 169 | except Exception as e:
 170 |     logging.warning("Could not list routes: %s", e)
 171 | 
 172 | if __name__ == "__main__":
 173 |     port = int(os.environ.get("PORT", 5000))
 174 |     print(f"Starting Protocol Pulse → http://127.0.0.1:{port}/ (debug routes: http://127.0.0.1:{port}/debug-routes)")
 175 |     # Disable reloader so the process that binds the port is the same one that loaded routes (avoids 404 from reloader child)
 176 |     app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
 177 | 
```

### File: core/models.py (1020 lines)
```
   1 | import json
   2 | from datetime import datetime, timedelta
   3 | from flask_login import UserMixin
   4 | from werkzeug.security import generate_password_hash, check_password_hash
   5 | from app import db  # This stays here; we will fix the 'loop' in app.py
   6 | 
   7 | # =====================================
   8 | # USER & OPERATIVE MODELS
   9 | # =====================================
  10 | 
  11 | class User(UserMixin, db.Model):
  12 |     id = db.Column(db.Integer, primary_key=True)
  13 |     username = db.Column(db.String(80), unique=True, nullable=False)
  14 |     email = db.Column(db.String(120), unique=True, nullable=False)
  15 |     password_hash = db.Column(db.String(256))
  16 |     is_admin = db.Column(db.Boolean, default=False)
  17 |     newsletter_subscribed = db.Column(db.Boolean, default=False)
  18 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
  19 |     
  20 |     operative_rank = db.Column(db.Integer, default=1)
  21 |     drill_completions = db.Column(db.Integer, default=0)
  22 |     brief_clicks = db.Column(db.Integer, default=0)
  23 |     operative_slug = db.Column(db.String(100), unique=True)
  24 |     crm_synced_at = db.Column(db.DateTime)
  25 |     last_drill_at = db.Column(db.DateTime)
  26 |     last_brief_at = db.Column(db.DateTime)
  27 |     
  28 |     # Premium subscription (free | operator | commander | sovereign)
  29 |     subscription_tier = db.Column(db.String(30), default='free')
  30 |     stripe_customer_id = db.Column(db.String(120))
  31 |     stripe_subscription_id = db.Column(db.String(120))
  32 |     subscription_expires_at = db.Column(db.DateTime)
  33 |     # Commander+: opt-in to email alerts for mega whales (≥1000 BTC)
  34 |     mega_whale_email_alerts = db.Column(db.Boolean, default=False)
  35 |     
  36 |     # --- Auth Methods ---
  37 |     def set_password(self, password):
  38 |         self.password_hash = generate_password_hash(password)
  39 | 
  40 |     def check_password(self, password):
  41 |         return check_password_hash(self.password_hash, password)
  42 | 
  43 |     # --- Operative Logic ---
  44 |     def get_rank_name(self):
  45 |         if self.operative_rank >= 3:
  46 |             return 'SOVEREIGN ELITE'
  47 |         elif self.operative_rank >= 2:
  48 |             return 'OPERATIVE'
  49 |         return 'RECRUIT'
  50 |     
  51 |     def check_rank_progression(self):
  52 |         if self.drill_completions >= 5 and self.brief_clicks >= 10:
  53 |             self.operative_rank = 3
  54 |         elif self.drill_completions >= 1:
  55 |             self.operative_rank = 2
  56 |         else:
  57 |             self.operative_rank = 1
  58 |     
  59 |     def generate_operative_slug(self):
  60 |         import hashlib
  61 |         import time
  62 |         if not self.operative_slug:
  63 |             base = self.username.lower().replace(' ', '-')[:20]
  64 |             unique_hash = hashlib.md5(f"{self.email}{time.time()}".encode()).hexdigest()[:6]
  65 |             self.operative_slug = f"{base}-{unique_hash}"
  66 |         return self.operative_slug
  67 |     
  68 |     def can_increment_drill(self):
  69 |         if not self.last_drill_at:
  70 |             return True
  71 |         cooldown = datetime.utcnow() - self.last_drill_at
  72 |         return cooldown.total_seconds() >= 300
  73 |     
  74 |     def can_increment_brief(self):
  75 |         if not self.last_brief_at:
  76 |             return True
  77 |         cooldown = datetime.utcnow() - self.last_brief_at
  78 |         return cooldown.total_seconds() >= 60
  79 |     
  80 |     def has_premium(self):
  81 |         """True if user has any paid tier (operator, commander, sovereign)."""
  82 |         tier = getattr(self, 'subscription_tier', None)
  83 |         return tier and tier != 'free'
  84 | 
  85 |     def has_commander_tier(self):
  86 |         """True if user has $99/mo Commander (or higher) tier."""
  87 |         tier = getattr(self, 'subscription_tier', None)
  88 |         return tier in ('commander', 'sovereign')
  89 | 
  90 | # =====================================
  91 | # CONTENT & INTELLIGENCE MODELS
  92 | # =====================================
  93 | 
  94 | class Article(db.Model):
  95 |     __tablename__ = "articles"
  96 |     id = db.Column(db.Integer, primary_key=True)
  97 |     title = db.Column(db.String(200), nullable=False)
  98 |     content = db.Column(db.Text, nullable=False)
  99 |     summary = db.Column(db.Text)
 100 |     author = db.Column(db.String(100), default="Protocol Pulse AI")
 101 |     category = db.Column(db.String(50), default="Web3")
 102 |     tags = db.Column(db.String(500))
 103 |     source_url = db.Column(db.String(500))
 104 |     source_type = db.Column(db.String(50))
 105 |     featured = db.Column(db.Boolean, default=False)
 106 |     published = db.Column(db.Boolean, default=False)
 107 |     # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
 108 |     premium_tier = db.Column(db.String(30), default=None)
 109 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 110 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 111 |     seo_title = db.Column(db.String(200))
 112 |     seo_description = db.Column(db.String(300))
 113 |     substack_url = db.Column(db.String(500))
 114 |     header_image_url = db.Column(db.String(500))
 115 |     screenshot_url = db.Column(db.String(500))
 116 |     video_url = db.Column(db.String(500))
 117 | 
 118 | class Podcast(db.Model):
 119 |     id = db.Column(db.Integer, primary_key=True)
 120 |     title = db.Column(db.String(200), nullable=False)
 121 |     description = db.Column(db.Text)
 122 |     host = db.Column(db.String(100))
 123 |     episode_number = db.Column(db.Integer)
 124 |     duration = db.Column(db.String(20))
 125 |     audio_url = db.Column(db.String(500))
 126 |     cover_image_url = db.Column(db.String(500))
 127 |     published_date = db.Column(db.DateTime, default=datetime.utcnow)
 128 |     featured = db.Column(db.Boolean, default=False)
 129 |     category = db.Column(db.String(50), default="Web3")
 130 |     rss_source = db.Column(db.String(100))
 131 | 
 132 | class ContentPrompt(db.Model):
 133 |     id = db.Column(db.Integer, primary_key=True)
 134 |     name = db.Column(db.String(100), nullable=False)
 135 |     prompt_text = db.Column(db.Text, nullable=False)
 136 |     category = db.Column(db.String(50))
 137 |     active = db.Column(db.Boolean, default=True)
 138 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 139 | 
 140 | class Advertisement(db.Model):
 141 |     id = db.Column(db.Integer, primary_key=True)
 142 |     name = db.Column(db.String(150), nullable=False)
 143 |     image_url = db.Column(db.String(300), nullable=False)
 144 |     target_url = db.Column(db.String(300), nullable=False)
 145 |     is_active = db.Column(db.Boolean, default=False)
 146 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 147 | 
 148 | 
 149 | class AffiliateProduct(db.Model):
 150 |     """Products we have affiliate links for (Amazon, Trezor, etc.) — used in product-highlight articles."""
 151 |     __tablename__ = 'affiliate_product'
 152 |     id = db.Column(db.Integer, primary_key=True)
 153 |     name = db.Column(db.String(200), nullable=False)
 154 |     product_type = db.Column(db.String(50), nullable=False)  # amazon_book, trezor, cold_wallet, seed_plate, miner, etc.
 155 |     product_id = db.Column(db.String(100))  # ASIN, offer_id, etc.
 156 |     affiliate_url = db.Column(db.String(500))
 157 |     category = db.Column(db.String(80))  # cold_wallet, seed_plate, bitaxe_miner, book, etc.
 158 |     short_description = db.Column(db.String(500))
 159 |     active = db.Column(db.Boolean, default=True)
 160 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 161 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 162 | 
 163 | 
 164 | class AffiliateProductClick(db.Model):
 165 |     """Track affiliate product link clicks for revenue analytics (Smart Analytics)."""
 166 |     __tablename__ = 'affiliate_product_click'
 167 |     id = db.Column(db.Integer, primary_key=True)
 168 |     product_id = db.Column(db.Integer, db.ForeignKey('affiliate_product.id'), nullable=True)
 169 |     link_type = db.Column(db.String(50))  # amazon, trezor, etc.
 170 |     page_path = db.Column(db.String(500))
 171 |     session_id = db.Column(db.String(64))
 172 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 173 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 174 | 
 175 | 
 176 | # =====================================
 177 | # AUTOMATION & LOGISTICS
 178 | # =====================================
 179 | 
 180 | class AutomationRun(db.Model):
 181 |     id = db.Column(db.Integer, primary_key=True)
 182 |     task_name = db.Column(db.String(100), nullable=False)
 183 |     started_at = db.Column(db.DateTime, nullable=False)
 184 |     finished_at = db.Column(db.DateTime)
 185 |     status = db.Column(db.String(20))
 186 |     error = db.Column(db.String(500))
 187 | 
 188 | class LaunchSequence(db.Model):
 189 |     id = db.Column(db.Integer, primary_key=True)
 190 |     content_id = db.Column(db.Integer)
 191 |     content_type = db.Column(db.String(50))
 192 |     primary_post_copy = db.Column(db.Text)
 193 |     thread_replies = db.Column(db.Text)
 194 |     quote_variants = db.Column(db.Text)
 195 |     reply_drafts = db.Column(db.Text)
 196 |     hashtags = db.Column(db.String(500))
 197 |     posting_time = db.Column(db.Time)
 198 |     velocity_prediction = db.Column(db.Float)
 199 |     first_reply_link = db.Column(db.String(500))
 200 |     call_to_action = db.Column(db.String(300))
 201 |     status = db.Column(db.String(50), default='draft')
 202 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 203 |     approved_at = db.Column(db.DateTime)
 204 |     published_at = db.Column(db.DateTime)
 205 |     tweet_id = db.Column(db.String(100))
 206 |     actual_velocity_score = db.Column(db.Float)
 207 |     replies_first_5min = db.Column(db.Integer, default=0)
 208 |     total_engagement = db.Column(db.Integer, default=0)
 209 |     reached_for_you = db.Column(db.Boolean, default=False)
 210 |     dispatch_window = db.Column(db.String(20))
 211 |     dispatch_timezone = db.Column(db.String(50), default='America/New_York')
 212 |     persona_debate = db.Column(db.Text)
 213 |     is_autonomous = db.Column(db.Boolean, default=False)
 214 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 215 |     ground_truth = db.Column(db.Text)
 216 |     target_segment = db.Column(db.String(100))
 217 |     generated_by = db.Column(db.String(50))
 218 |     nostr_event_id = db.Column(db.String(100))
 219 |     x_tweet_id = db.Column(db.String(100))
 220 |     is_approved = db.Column(db.Boolean, default=False)
 221 |     is_posted = db.Column(db.Boolean, default=False)
 222 | 
 223 | class TargetAlert(db.Model):
 224 |     id = db.Column(db.Integer, primary_key=True)
 225 |     trigger_type = db.Column(db.String(50))
 226 |     source_url = db.Column(db.String(500))
 227 |     source_account = db.Column(db.String(100))
 228 |     content_snippet = db.Column(db.Text)
 229 |     priority = db.Column(db.Integer, default=2)
 230 |     strategy_suggested = db.Column(db.String(100))
 231 |     draft_replies = db.Column(db.Text)
 232 |     status = db.Column(db.String(50), default='pending')
 233 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 234 |     responded_at = db.Column(db.DateTime)
 235 | 
 236 | class NostrEvent(db.Model):
 237 |     id = db.Column(db.Integer, primary_key=True)
 238 |     event_id = db.Column(db.String(100))
 239 |     content_type = db.Column(db.String(50))
 240 |     content_id = db.Column(db.Integer)
 241 |     relays_success = db.Column(db.Text)
 242 |     relays_failed = db.Column(db.Text)
 243 |     zaps_received = db.Column(db.Integer, default=0)
 244 |     zaps_amount_sats = db.Column(db.Integer, default=0)
 245 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 246 | 
 247 | class ReplySquadMember(db.Model):
 248 |     id = db.Column(db.Integer, primary_key=True)
 249 |     handle = db.Column(db.String(100), nullable=False)
 250 |     display_name = db.Column(db.String(150))
 251 |     category = db.Column(db.String(100))
 252 |     priority = db.Column(db.Integer, default=2)
 253 |     reciprocal_engagements = db.Column(db.Integer, default=0)
 254 |     last_engagement = db.Column(db.DateTime)
 255 |     notes = db.Column(db.Text)
 256 |     active = db.Column(db.Boolean, default=True)
 257 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 258 | 
 259 | # =====================================
 260 | # BITCOIN NETWORK & DONATIONS
 261 | # =====================================
 262 | 
 263 | class WhaleTransaction(db.Model):
 264 |     id = db.Column(db.Integer, primary_key=True)
 265 |     txid = db.Column(db.String(100), unique=True, nullable=False)
 266 |     btc_amount = db.Column(db.Float, nullable=False)
 267 |     usd_value = db.Column(db.Float)
 268 |     fee_sats = db.Column(db.Integer)
 269 |     block_height = db.Column(db.Integer)
 270 |     detected_at = db.Column(db.DateTime, default=datetime.utcnow)
 271 |     is_mega = db.Column(db.Boolean, default=False)
 272 | 
 273 | 
 274 | class ContactSubmission(db.Model):
 275 |     """Contact form submissions (stored for admin; optional email notification)."""
 276 |     id = db.Column(db.Integer, primary_key=True)
 277 |     name = db.Column(db.String(200), nullable=False)
 278 |     email = db.Column(db.String(200), nullable=False)
 279 |     subject = db.Column(db.String(100), nullable=False)
 280 |     message = db.Column(db.Text, nullable=False)
 281 |     ip_address = db.Column(db.String(64))
 282 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 283 |     read = db.Column(db.Boolean, default=False)
 284 | 
 285 | 
 286 | class PremiumAsk(db.Model):
 287 |     """Sovereign Elite monthly ask: one research/question per month, answered by team."""
 288 |     id = db.Column(db.Integer, primary_key=True)
 289 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 290 |     question_text = db.Column(db.Text, nullable=False)
 291 |     status = db.Column(db.String(20), default='pending')  # pending | answered
 292 |     answer_text = db.Column(db.Text)
 293 |     answer_url = db.Column(db.String(500))  # optional link to brief or doc
 294 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 295 |     answered_at = db.Column(db.DateTime)
 296 |     user = db.relationship('User', backref=db.backref('premium_asks', lazy='dynamic'))
 297 | 
 298 | 
 299 | class BitcoinDonation(db.Model):
 300 |     id = db.Column(db.Integer, primary_key=True)
 301 |     payment_id = db.Column(db.String(100))
 302 |     amount_sats = db.Column(db.Integer)
 303 |     amount_usd = db.Column(db.Float)
 304 |     donor_email = db.Column(db.String(200))
 305 |     donor_name = db.Column(db.String(200))
 306 |     message = db.Column(db.Text)
 307 |     status = db.Column(db.String(50), default='pending')
 308 |     payment_method = db.Column(db.String(50))
 309 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 310 |     confirmed_at = db.Column(db.DateTime)
 311 | 
 312 | # =====================================
 313 | # ANALYTICS & PERFORMANCE
 314 | # =====================================
 315 | 
 316 | class EngagementEvent(db.Model):
 317 |     id = db.Column(db.Integer, primary_key=True)
 318 |     event_type = db.Column(db.String(50), nullable=False)
 319 |     content_type = db.Column(db.String(50))
 320 |     content_id = db.Column(db.Integer)
 321 |     source_platform = db.Column(db.String(50))
 322 |     source_url = db.Column(db.String(500))
 323 |     persona = db.Column(db.String(50))
 324 |     strategy = db.Column(db.String(100))
 325 |     minutes_after_post = db.Column(db.Float)
 326 |     is_30min_window = db.Column(db.Boolean, default=False)
 327 |     grok_score_contribution = db.Column(db.Integer, default=0)
 328 |     user_agent = db.Column(db.String(300))
 329 |     referrer = db.Column(db.String(500))
 330 |     ip_hash = db.Column(db.String(64))
 331 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 332 | 
 333 | class ContentPerformance(db.Model):
 334 |     id = db.Column(db.Integer, primary_key=True)
 335 |     content_type = db.Column(db.String(50), nullable=False)
 336 |     content_id = db.Column(db.Integer, nullable=False)
 337 |     content_title = db.Column(db.String(300))
 338 |     total_views = db.Column(db.Integer, default=0)
 339 |     total_clicks = db.Column(db.Integer, default=0)
 340 |     total_replies = db.Column(db.Integer, default=0)
 341 |     total_retweets = db.Column(db.Integer, default=0)
 342 |     total_quotes = db.Column(db.Integer, default=0)
 343 |     total_likes = db.Column(db.Integer, default=0)
 344 |     profile_visits = db.Column(db.Integer, default=0)
 345 |     replies_0_5min = db.Column(db.Integer, default=0)
 346 |     replies_5_15min = db.Column(db.Integer, default=0)
 347 |     replies_15_30min = db.Column(db.Integer, default=0)
 348 |     replies_30plus_min = db.Column(db.Integer, default=0)
 349 |     velocity_score = db.Column(db.Float, default=0)
 350 |     grok_score_total = db.Column(db.Integer, default=0)
 351 |     reached_for_you = db.Column(db.Boolean, default=False)
 352 |     peak_velocity_minute = db.Column(db.Integer)
 353 |     alex_engagements = db.Column(db.Integer, default=0)
 354 |     sarah_engagements = db.Column(db.Integer, default=0)
 355 |     best_performing_strategy = db.Column(db.String(100))
 356 |     best_performing_time = db.Column(db.String(20))
 357 |     published_at = db.Column(db.DateTime)
 358 |     last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 359 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 360 | 
 361 | class AnalyticsSummary(db.Model):
 362 |     id = db.Column(db.Integer, primary_key=True)
 363 |     period_type = db.Column(db.String(20), nullable=False)
 364 |     period_start = db.Column(db.Date, nullable=False)
 365 |     period_end = db.Column(db.Date, nullable=False)
 366 |     total_posts = db.Column(db.Integer, default=0)
 367 |     total_impressions = db.Column(db.Integer, default=0)
 368 |     total_engagements = db.Column(db.Integer, default=0)
 369 |     total_profile_visits = db.Column(db.Integer, default=0)
 370 |     total_followers_gained = db.Column(db.Integer, default=0)
 371 |     avg_velocity_score = db.Column(db.Float, default=0)
 372 |     avg_grok_score = db.Column(db.Float, default=0)
 373 |     for_you_reach_rate = db.Column(db.Float, default=0)
 374 |     top_performing_content_id = db.Column(db.Integer)
 375 |     top_performing_content_type = db.Column(db.String(50))
 376 |     top_performing_strategy = db.Column(db.String(100))
 377 |     alex_total_score = db.Column(db.Integer, default=0)
 378 |     sarah_total_score = db.Column(db.Integer, default=0)
 379 |     persona_winner = db.Column(db.String(50))
 380 |     best_posting_hour = db.Column(db.Integer)
 381 |     best_posting_day = db.Column(db.Integer)
 382 |     sponsor_value_estimate = db.Column(db.Float)
 383 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 384 | 
 385 | class Sponsor(db.Model):
 386 |     id = db.Column(db.Integer, primary_key=True)
 387 |     name = db.Column(db.String(200), nullable=False)
 388 |     company = db.Column(db.String(200))
 389 |     email = db.Column(db.String(200))
 390 |     website_url = db.Column(db.String(500))
 391 |     logo_url = db.Column(db.String(500))
 392 |     tier = db.Column(db.String(50), default='standard')
 393 |     status = db.Column(db.String(50), default='pending')
 394 |     impressions = db.Column(db.Integer, default=0)
 395 |     clicks = db.Column(db.Integer, default=0)
 396 |     ctr = db.Column(db.Float, default=0)
 397 |     budget_sats = db.Column(db.Integer, default=0)
 398 |     spent_sats = db.Column(db.Integer, default=0)
 399 |     cpm_sats = db.Column(db.Integer, default=1000)
 400 |     target_categories = db.Column(db.String(500))
 401 |     target_personas = db.Column(db.String(200))
 402 |     ad_copy = db.Column(db.Text)
 403 |     cta_text = db.Column(db.String(100))
 404 |     cta_url = db.Column(db.String(500))
 405 |     start_date = db.Column(db.DateTime)
 406 |     end_date = db.Column(db.DateTime)
 407 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 408 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 409 | 
 410 | class CreditAccount(db.Model):
 411 |     id = db.Column(db.Integer, primary_key=True)
 412 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 413 |     signal_points = db.Column(db.Integer, default=0)
 414 |     lifetime_points = db.Column(db.Integer, default=0)
 415 |     tier = db.Column(db.String(50), default='recruit')
 416 |     tier_progress = db.Column(db.Float, default=0)
 417 |     articles_read = db.Column(db.Integer, default=0)
 418 |     podcasts_listened = db.Column(db.Integer, default=0)
 419 |     quizzes_completed = db.Column(db.Integer, default=0)
 420 |     referrals_made = db.Column(db.Integer, default=0)
 421 |     streak_days = db.Column(db.Integer, default=0)
 422 |     longest_streak = db.Column(db.Integer, default=0)
 423 |     last_activity = db.Column(db.DateTime)
 424 |     badges = db.Column(db.Text)
 425 |     achievements = db.Column(db.Text)
 426 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 427 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 428 |     user = db.relationship('User', backref=db.backref('credit_account', uselist=False))
 429 | 
 430 | class PredictionOracle(db.Model):
 431 |     id = db.Column(db.Integer, primary_key=True)
 432 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 433 |     prediction_type = db.Column(db.String(50))
 434 |     prediction_value = db.Column(db.Float)
 435 |     target_date = db.Column(db.DateTime)
 436 |     actual_value = db.Column(db.Float)
 437 |     accuracy_score = db.Column(db.Float)
 438 |     status = db.Column(db.String(50), default='pending')
 439 |     is_correct = db.Column(db.Boolean)
 440 |     signal_points_wagered = db.Column(db.Integer, default=0)
 441 |     signal_points_won = db.Column(db.Integer, default=0)
 442 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 443 |     resolved_at = db.Column(db.DateTime)
 444 | 
 445 | class UserSegment(db.Model):
 446 |     id = db.Column(db.Integer, primary_key=True)
 447 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 448 |     segment_type = db.Column(db.String(50), default='general')
 449 |     confidence = db.Column(db.Float, default=0.5)
 450 |     hashrate_interest = db.Column(db.Float, default=0)
 451 |     macro_interest = db.Column(db.Float, default=0)
 452 |     technical_interest = db.Column(db.Float, default=0)
 453 |     trading_interest = db.Column(db.Float, default=0)
 454 |     privacy_interest = db.Column(db.Float, default=0)
 455 |     articles_viewed = db.Column(db.Integer, default=0)
 456 |     avg_read_time = db.Column(db.Float, default=0)
 457 |     preferred_categories = db.Column(db.Text)
 458 |     last_classification = db.Column(db.DateTime, default=datetime.utcnow)
 459 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 460 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 461 |     user = db.relationship('User', backref=db.backref('segment', uselist=False))
 462 | 
 463 | class AffiliatePartner(db.Model):
 464 |     __tablename__ = 'affiliate_partner'
 465 |     id = db.Column(db.Integer, primary_key=True)
 466 |     name = db.Column(db.String(100), unique=True, nullable=False)
 467 |     slug = db.Column(db.String(50), unique=True, nullable=False)
 468 |     category = db.Column(db.String(50))
 469 |     url = db.Column(db.String(500))
 470 |     benefit = db.Column(db.String(200))
 471 |     is_active = db.Column(db.Boolean, default=True)
 472 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 473 |     clicks = db.relationship('AffiliateClick', backref='partner', lazy='dynamic')
 474 | 
 475 | class AffiliateClick(db.Model):
 476 |     __tablename__ = 'affiliate_click'
 477 |     id = db.Column(db.Integer, primary_key=True)
 478 |     partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=False)
 479 |     source_page = db.Column(db.String(500))
 480 |     ip_hash = db.Column(db.String(64))
 481 |     user_agent = db.Column(db.String(500))
 482 |     clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
 483 | 
 484 | class FeedItem(db.Model):
 485 |     __tablename__ = 'feed_item'
 486 |     id = db.Column(db.Integer, primary_key=True)
 487 |     source = db.Column(db.String(100), nullable=False)
 488 |     source_type = db.Column(db.String(50), nullable=False)
 489 |     tier = db.Column(db.String(20))
 490 |     title = db.Column(db.String(500))
 491 |     url = db.Column(db.String(1000), unique=True)
 492 |     published_at = db.Column(db.DateTime)
 493 |     author = db.Column(db.String(100))
 494 |     summary = db.Column(db.Text)
 495 |     platform_icon = db.Column(db.String(50))
 496 |     raw_json = db.Column(db.Text)
 497 |     verified = db.Column(db.Boolean, default=False)
 498 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 499 | 
 500 | class SentimentSnapshot(db.Model):
 501 |     __tablename__ = 'sentiment_snapshot'
 502 |     id = db.Column(db.Integer, primary_key=True)
 503 |     score = db.Column(db.Float, default=50.0)
 504 |     state = db.Column(db.String(50), default='EQUILIBRIUM')
 505 |     state_label = db.Column(db.String(50), default='EQUILIBRIUM')
 506 |     state_color = db.Column(db.String(20), default='#ffffff')
 507 |     velocity = db.Column(db.Float, default=0.0)
 508 |     top_keywords = db.Column(db.Text)
 509 |     top_topics_json = db.Column(db.Text)
 510 |     sample_size = db.Column(db.Integer, default=0)
 511 |     verified_weight = db.Column(db.Integer, default=0)
 512 |     computed_at = db.Column(db.DateTime, default=datetime.utcnow)
 513 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 514 | 
 515 | class PulseEvent(db.Model):
 516 |     __tablename__ = 'pulse_event'
 517 |     id = db.Column(db.Integer, primary_key=True)
 518 |     event_type = db.Column(db.String(50), nullable=False)
 519 |     from_state = db.Column(db.String(50))
 520 |     to_state = db.Column(db.String(50))
 521 |     score = db.Column(db.Float)
 522 |     triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
 523 |     payload_json = db.Column(db.Text)
 524 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 525 | 
 526 | class AutoPostDraft(db.Model):
 527 |     __tablename__ = 'autopost_draft'
 528 |     id = db.Column(db.Integer, primary_key=True)
 529 |     platform = db.Column(db.String(30), nullable=False)
 530 |     status = db.Column(db.String(20), default='draft')
 531 |     body = db.Column(db.Text)
 532 |     reason = db.Column(db.String(200))
 533 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 534 |     approved_at = db.Column(db.DateTime)
 535 |     posted_at = db.Column(db.DateTime)
 536 | 
 537 | class DailyBrief(db.Model):
 538 |     __tablename__ = 'daily_brief'
 539 |     id = db.Column(db.Integer, primary_key=True)
 540 |     headline = db.Column(db.String(500))
 541 |     body = db.Column(db.Text)
 542 |     signals_json = db.Column(db.Text)
 543 |     status = db.Column(db.String(20), default='draft')
 544 |     published_at = db.Column(db.DateTime)
 545 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 546 | 
 547 | class PageView(db.Model):
 548 |     __tablename__ = 'page_view'
 549 |     id = db.Column(db.Integer, primary_key=True)
 550 |     page_path = db.Column(db.String(500), nullable=False)
 551 |     page_title = db.Column(db.String(300))
 552 |     page_category = db.Column(db.String(50))
 553 |     session_id = db.Column(db.String(64))
 554 |     ip_hash = db.Column(db.String(64))
 555 |     user_agent = db.Column(db.String(300))
 556 |     referrer = db.Column(db.String(500))
 557 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 558 |     time_on_page = db.Column(db.Integer, default=0)
 559 |     scroll_depth = db.Column(db.Integer, default=0)
 560 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 561 | 
 562 | class HotMoment(db.Model):
 563 |     __tablename__ = 'hot_moment'
 564 |     id = db.Column(db.Integer, primary_key=True)
 565 |     page_path = db.Column(db.String(500), nullable=False)
 566 |     page_title = db.Column(db.String(300))
 567 |     page_category = db.Column(db.String(50))
 568 |     views_in_window = db.Column(db.Integer, default=0)
 569 |     unique_visitors = db.Column(db.Integer, default=0)
 570 |     heat_score = db.Column(db.Float, default=0)
 571 |     is_peak = db.Column(db.Boolean, default=False)
 572 |     peak_detected_at = db.Column(db.DateTime)
 573 |     tweet_drafted = db.Column(db.Boolean, default=False)
 574 |     tweet_content = db.Column(db.Text)
 575 |     tweet_posted_at = db.Column(db.DateTime)
 576 |     window_start = db.Column(db.DateTime, nullable=False)
 577 |     window_end = db.Column(db.DateTime, nullable=False)
 578 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 579 | 
 580 | class ContentSuggestion(db.Model):
 581 |     __tablename__ = 'content_suggestion'
 582 |     id = db.Column(db.Integer, primary_key=True)
 583 |     suggestion_type = db.Column(db.String(50))
 584 |     title = db.Column(db.String(300))
 585 |     description = db.Column(db.Text)
 586 |     reasoning = db.Column(db.Text)
 587 |     based_on_page = db.Column(db.String(500))
 588 |     based_on_trend = db.Column(db.String(200))
 589 |     confidence_score = db.Column(db.Float, default=0)
 590 |     status = db.Column(db.String(20), default='pending')
 591 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 592 |     actioned_at = db.Column(db.DateTime)
 593 | 
 594 | class AutoTweet(db.Model):
 595 |     __tablename__ = 'auto_tweet'
 596 |     id = db.Column(db.Integer, primary_key=True)
 597 |     trigger_type = db.Column(db.String(50))
 598 |     trigger_page = db.Column(db.String(500))
 599 |     heat_score_at_trigger = db.Column(db.Float)
 600 |     tweet_content = db.Column(db.Text, nullable=False)
 601 |     hashtags = db.Column(db.String(200))
 602 |     status = db.Column(db.String(20), default='draft')
 603 |     approved_at = db.Column(db.DateTime)
 604 |     posted_at = db.Column(db.DateTime)
 605 |     post_url = db.Column(db.String(500))
 606 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 607 | 
 608 | 
 609 | # =====================================
 610 | # X ENGAGEMENT SENTRY (TWEET REPLIES)
 611 | # =====================================
 612 | 
 613 | 
 614 | class XInboxTweet(db.Model):
 615 |     """Incoming tweets from monitored X accounts for Sovereign Sentry."""
 616 |     __tablename__ = 'x_inbox_tweet'
 617 | 
 618 |     id = db.Column(db.Integer, primary_key=True)
 619 |     tweet_id = db.Column(db.String(64), unique=True, nullable=False)
 620 |     author_handle = db.Column(db.String(50), nullable=False, index=True)
 621 |     author_name = db.Column(db.String(100))
 622 |     tweet_text = db.Column(db.Text, nullable=False)
 623 |     tweet_url = db.Column(db.String(500))
 624 |     tweet_created_at = db.Column(db.DateTime)
 625 |     status = db.Column(
 626 |         db.String(20),
 627 |         default='new',
 628 |     )  # new | drafted | approved | posted | rejected | skipped | error
 629 |     tier = db.Column(db.String(30))
 630 |     style = db.Column(db.String(30))
 631 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 632 | 
 633 | 
 634 | class XReplyDraft(db.Model):
 635 |     """Generated reply drafts evaluated by Sovereign Sentry."""
 636 |     __tablename__ = 'x_reply_draft'
 637 | 
 638 |     id = db.Column(db.Integer, primary_key=True)
 639 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 640 |     draft_text = db.Column(db.String(300), nullable=False)
 641 |     confidence = db.Column(db.Float)
 642 |     reasoning = db.Column(db.Text)
 643 |     style_used = db.Column(db.String(30))
 644 |     risk_flags = db.Column(db.Text)  # optional JSON array string
 645 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 646 | 
 647 |     inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))
 648 | 
 649 | 
 650 | class XReplyPost(db.Model):
 651 |     """Log of replies actually posted to X."""
 652 |     __tablename__ = 'x_reply_post'
 653 | 
 654 |     id = db.Column(db.Integer, primary_key=True)
 655 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 656 |     draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
 657 |     reply_tweet_id = db.Column(db.String(64))
 658 |     posted_at = db.Column(db.DateTime, default=datetime.utcnow)
 659 |     response_payload = db.Column(db.Text)  # raw JSON from X API
 660 | 
 661 |     inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
 662 |     draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))
 663 | 
 664 | 
 665 | # =====================================
 666 | # VALUE STREAM MODELS
 667 | # =====================================
 668 | 
 669 | class ValueCreator(db.Model):
 670 |     __tablename__ = 'value_creator'
 671 |     id = db.Column(db.Integer, primary_key=True)
 672 |     display_name = db.Column(db.String(100), nullable=False)
 673 |     nostr_pubkey = db.Column(db.String(128), unique=True)
 674 |     lightning_address = db.Column(db.String(200))
 675 |     nip05 = db.Column(db.String(200))
 676 |     twitter_handle = db.Column(db.String(50))
 677 |     youtube_channel_id = db.Column(db.String(50))
 678 |     reddit_username = db.Column(db.String(50))
 679 |     stacker_news_username = db.Column(db.String(50))
 680 |     profile_image = db.Column(db.String(500))
 681 |     bio = db.Column(db.Text)
 682 |     total_sats_received = db.Column(db.BigInteger, default=0)
 683 |     total_zaps = db.Column(db.Integer, default=0)
 684 |     curator_score = db.Column(db.Float, default=0)
 685 |     verified = db.Column(db.Boolean, default=False)
 686 |     verified_at = db.Column(db.DateTime)
 687 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 688 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 689 |     curated_posts = db.relationship('CuratedPost', backref='creator', lazy='dynamic',
 690 |                                      foreign_keys='CuratedPost.creator_id')
 691 |     submitted_posts = db.relationship('CuratedPost', backref='curator', lazy='dynamic',
 692 |                                        foreign_keys='CuratedPost.curator_id')
 693 | 
 694 | class CuratedPost(db.Model):
 695 |     __tablename__ = 'curated_post'
 696 |     id = db.Column(db.Integer, primary_key=True)
 697 |     platform = db.Column(db.String(30), nullable=False)
 698 |     original_url = db.Column(db.String(1000), nullable=False, unique=True)
 699 |     original_id = db.Column(db.String(200))
 700 |     title = db.Column(db.String(500))
 701 |     content_preview = db.Column(db.Text)
 702 |     thumbnail_url = db.Column(db.String(500))
 703 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 704 |     curator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 705 |     total_sats = db.Column(db.BigInteger, default=0)
 706 |     zap_count = db.Column(db.Integer, default=0)
 707 |     boost_sats = db.Column(db.BigInteger, default=0)
 708 |     signal_score = db.Column(db.Float, default=0)
 709 |     decay_factor = db.Column(db.Float, default=1.0)
 710 |     is_verified = db.Column(db.Boolean, default=False)
 711 |     is_featured = db.Column(db.Boolean, default=False)
 712 |     submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
 713 |     last_zap_at = db.Column(db.DateTime)
 714 |     
 715 |     def calculate_signal_score(self):
 716 |         age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
 717 |         time_decay = max(0.1, 1 - (age_hours / 168))
 718 |         raw_score = (self.total_sats * 0.001) + (self.zap_count * 10)
 719 |         self.signal_score = raw_score * time_decay * self.decay_factor
 720 |         return self.signal_score
 721 | 
 722 | class ZapEvent(db.Model):
 723 |     __tablename__ = 'zap_event'
 724 |     id = db.Column(db.Integer, primary_key=True)
 725 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 726 |     sender_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 727 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 728 |     creator_share = db.Column(db.BigInteger)
 729 |     curator_share = db.Column(db.BigInteger)
 730 |     platform_share = db.Column(db.BigInteger)
 731 |     payment_hash = db.Column(db.String(128))
 732 |     bolt11_invoice = db.Column(db.Text)
 733 |     preimage = db.Column(db.String(128))
 734 |     status = db.Column(db.String(20), default='pending')
 735 |     source = db.Column(db.String(30))
 736 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 737 |     settled_at = db.Column(db.DateTime)
 738 |     post = db.relationship('CuratedPost', backref=db.backref('zaps', lazy='dynamic'))
 739 | 
 740 | class TrustEdge(db.Model):
 741 |     __tablename__ = 'trust_edge'
 742 |     id = db.Column(db.Integer, primary_key=True)
 743 |     truster_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 744 |     trusted_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 745 |     trust_weight = db.Column(db.Float, default=1.0)
 746 |     total_sats_via = db.Column(db.BigInteger, default=0)
 747 |     successful_curations = db.Column(db.Integer, default=0)
 748 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 749 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 750 |     __table_args__ = (db.UniqueConstraint('truster_id', 'trusted_id', name='unique_trust_edge'),)
 751 | 
 752 | class BoostStake(db.Model):
 753 |     __tablename__ = 'boost_stake'
 754 |     id = db.Column(db.Integer, primary_key=True)
 755 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 756 |     staker_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 757 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 758 |     boost_multiplier = db.Column(db.Float, default=1.0)
 759 |     expires_at = db.Column(db.DateTime)
 760 |     refunded = db.Column(db.Boolean, default=False)
 761 |     refund_amount = db.Column(db.BigInteger, default=0)
 762 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 763 |     post = db.relationship('CuratedPost', backref=db.backref('boosts', lazy='dynamic'))
 764 | 
 765 | class ExtensionSession(db.Model):
 766 |     __tablename__ = 'extension_session'
 767 |     id = db.Column(db.Integer, primary_key=True)
 768 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 769 |     session_token = db.Column(db.String(128), unique=True, nullable=False)
 770 |     browser_fingerprint = db.Column(db.String(128))
 771 |     user_agent = db.Column(db.String(500))
 772 |     is_active = db.Column(db.Boolean, default=True)
 773 |     last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
 774 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 775 |     expires_at = db.Column(db.DateTime)
 776 |     creator = db.relationship('ValueCreator', backref=db.backref('sessions', lazy='dynamic'))
 777 | 
 778 | class RollingActivity(db.Model):
 779 |     __tablename__ = 'rolling_activity'
 780 |     id = db.Column(db.Integer, primary_key=True)
 781 |     page_path = db.Column(db.String(500), nullable=False, index=True)
 782 |     page_name = db.Column(db.String(200))
 783 |     session_hash = db.Column(db.String(64), nullable=False)
 784 |     last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 785 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 786 |     
 787 |     @classmethod
 788 |     def record_activity(cls, page_path, page_name, session_hash):
 789 |         existing = cls.query.filter_by(page_path=page_path, session_hash=session_hash).first()
 790 |         if existing:
 791 |             existing.last_seen = datetime.utcnow()
 792 |         else:
 793 |             activity = cls(page_path=page_path, page_name=page_name, session_hash=session_hash, last_seen=datetime.utcnow())
 794 |             db.session.add(activity)
 795 |         try:
 796 |             db.session.commit()
 797 |         except Exception:
 798 |             db.session.rollback()
 799 | 
 800 |     @classmethod
 801 |     def get_operative_density(cls, window_minutes=30, limit=5):
 802 |         from sqlalchemy import func
 803 |         cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
 804 |         results = db.session.query(cls.page_path, cls.page_name, func.count(func.distinct(cls.session_hash)).label('count')).filter(cls.last_seen >= cutoff).group_by(cls.page_path, cls.page_name).order_by(func.count(func.distinct(cls.session_hash)).desc()).limit(limit).all()
 805 |         return results
 806 | 
 807 | class RealTimeProduct(db.Model):
 808 |     __tablename__ = 'realtime_product'
 809 |     id = db.Column(db.Integer, primary_key=True)
 810 |     statement_text = db.Column(db.String(100), nullable=False)
 811 |     design_url = db.Column(db.String(500))
 812 |     design_style = db.Column(db.String(50), default='center_chest')
 813 |     text_color = db.Column(db.String(20), default='#FFFFFF')
 814 |     trigger_state = db.Column(db.String(50))
 815 |     trigger_keywords = db.Column(db.Text)
 816 |     sentiment_score = db.Column(db.Float)
 817 |     status = db.Column(db.String(20), default='draft')
 818 |     approved_at = db.Column(db.DateTime)
 819 |     approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
 820 |     printful_product_id = db.Column(db.String(100))
 821 |     printful_sync_status = db.Column(db.String(50), default='pending')
 822 |     heat_multiplier = db.Column(db.Float, default=2.0)
 823 |     heat_expires_at = db.Column(db.DateTime)
 824 |     sarah_description = db.Column(db.Text)
 825 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 826 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 827 |     
 828 |     def is_hot(self):
 829 |         return self.heat_expires_at and datetime.utcnow() < self.heat_expires_at
 830 | 
 831 | class IntelligencePost(db.Model):
 832 |     id = db.Column(db.Integer, primary_key=True)
 833 |     persona = db.Column(db.String(20))
 834 |     partner_name = db.Column(db.String(100))
 835 |     partner_handle = db.Column(db.String(100))
 836 |     primary_tweet = db.Column(db.Text, nullable=False)
 837 |     thread_content = db.Column(db.Text)
 838 |     key_insight = db.Column(db.Text)
 839 |     source_video_id = db.Column(db.String(50))
 840 |     source_video_title = db.Column(db.String(500))
 841 |     x_tweet_id = db.Column(db.String(100))
 842 |     nostr_event_id = db.Column(db.String(100))
 843 |     engagement_likes = db.Column(db.Integer, default=0)
 844 |     engagement_retweets = db.Column(db.Integer, default=0)
 845 |     engagement_replies = db.Column(db.Integer, default=0)
 846 |     published_at = db.Column(db.DateTime, default=datetime.utcnow)
 847 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 848 | 
 849 | class SentimentReport(db.Model):
 850 |     id = db.Column(db.Integer, primary_key=True)
 851 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 852 |     report_date = db.Column(db.Date, nullable=False, unique=True)
 853 |     overall_sentiment = db.Column(db.String(20))
 854 |     sentiment_score = db.Column(db.Float)
 855 |     x_posts_analyzed = db.Column(db.Integer, default=0)
 856 |     nostr_notes_analyzed = db.Column(db.Integer, default=0)
 857 |     top_themes = db.Column(db.Text)
 858 |     key_narratives = db.Column(db.Text)
 859 |     cited_sources = db.Column(db.Text)
 860 |     raw_analysis = db.Column(db.Text)
 861 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 862 |     article = db.relationship('Article', backref='sentiment_report', lazy=True)
 863 | 
 864 | class SarahBrief(db.Model):
 865 |     __tablename__ = 'sarah_brief'
 866 |     id = db.Column(db.Integer, primary_key=True)
 867 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 868 |     brief_date = db.Column(db.Date, nullable=False, unique=True)
 869 |     macro_state = db.Column(db.Text)
 870 |     network_calibration = db.Column(db.Text)
 871 |     signal_1_title = db.Column(db.String(500))
 872 |     signal_1_source = db.Column(db.String(500))
 873 |     signal_1_url = db.Column(db.String(500))
 874 |     signal_1_impact = db.Column(db.Float, default=0.0)
 875 |     signal_2_title = db.Column(db.String(500))
 876 |     signal_2_source = db.Column(db.String(500))
 877 |     signal_2_url = db.Column(db.String(500))
 878 |     signal_2_impact = db.Column(db.Float, default=0.0)
 879 |     signal_3_title = db.Column(db.String(500))
 880 |     signal_3_source = db.Column(db.String(500))
 881 |     signal_3_url = db.Column(db.String(500))
 882 |     signal_3_impact = db.Column(db.Float, default=0.0)
 883 |     mempool_state = db.Column(db.Text)
 884 |     hashrate_state = db.Column(db.Text)
 885 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 886 |     article = db.relationship('Article', backref='sarah_brief', lazy=True)
 887 | 
 888 | class SentimentBuffer(db.Model):
 889 |     id = db.Column(db.Integer, primary_key=True)
 890 |     timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 891 |     sentiment_score = db.Column(db.Float, nullable=False)
 892 |     post_count = db.Column(db.Integer, default=0)
 893 |     dominant_theme = db.Column(db.String(200))
 894 |     source_breakdown = db.Column(db.Text)
 895 | 
 896 | class EmergencyFlash(db.Model):
 897 |     id = db.Column(db.Integer, primary_key=True)
 898 |     triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 899 |     previous_score = db.Column(db.Float)
 900 |     current_score = db.Column(db.Float)
 901 |     drift_magnitude = db.Column(db.Float)
 902 |     direction = db.Column(db.String(20))
 903 |     trigger_reason = db.Column(db.Text)
 904 |     top_signal_url = db.Column(db.String(500))
 905 |     top_signal_author = db.Column(db.String(200))
 906 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 907 |     acknowledged = db.Column(db.Boolean, default=False)
 908 |     acknowledged_at = db.Column(db.DateTime)
 909 |     article = db.relationship('Article', backref='emergency_flash', lazy=True)
 910 | 
 911 | class CollectedSignal(db.Model):
 912 |     __tablename__ = 'collected_signal'
 913 |     id = db.Column(db.Integer, primary_key=True)
 914 |     platform = db.Column(db.String(20), nullable=False)
 915 |     post_id = db.Column(db.String(100), nullable=False, unique=True)
 916 |     author_name = db.Column(db.String(200), nullable=False)
 917 |     author_handle = db.Column(db.String(100), nullable=False)
 918 |     author_tier = db.Column(db.String(50), default='general')
 919 |     content = db.Column(db.Text, nullable=False)
 920 |     url = db.Column(db.String(500), nullable=False)
 921 |     engagement_likes = db.Column(db.Integer, default=0)
 922 |     engagement_reposts = db.Column(db.Integer, default=0)
 923 |     engagement_replies = db.Column(db.Integer, default=0)
 924 |     engagement_score = db.Column(db.Float, default=0.0)
 925 |     sentiment = db.Column(db.String(20))
 926 |     sentiment_score = db.Column(db.Float)
 927 |     is_bitcoin_related = db.Column(db.Boolean, default=True)
 928 |     posted_at = db.Column(db.DateTime)
 929 |     collected_at = db.Column(db.DateTime, default=datetime.utcnow)
 930 |     is_verified = db.Column(db.Boolean, default=True)
 931 |     is_legendary = db.Column(db.Boolean, default=False)
 932 |     __table_args__ = (
 933 |         db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
 934 |         db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
 935 |     )
 936 | 
 937 | 
 938 | # =====================================
 939 | # TERMINAL API SUBSCRIBER MODELS
 940 | # =====================================
 941 | 
 942 | class ApiSubscriber(db.Model):
 943 |     """Standalone API subscriber — email + Stripe + API key. No User account required."""
 944 |     __tablename__ = 'api_subscribers'
 945 | 
 946 |     id = db.Column(db.Integer, primary_key=True)
 947 |     email = db.Column(db.String(200), unique=True, nullable=False, index=True)
 948 |     api_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
 949 |     tier = db.Column(db.String(30), default='commander')  # commander|enterprise|demo
 950 |     stripe_customer_id = db.Column(db.String(120), index=True)
 951 |     stripe_subscription_id = db.Column(db.String(120), unique=True)
 952 |     stripe_price_id = db.Column(db.String(120))
 953 | 
 954 |     # Rate limiting
 955 |     rate_limit_per_hour = db.Column(db.Integer, default=1000)
 956 |     requests_this_hour = db.Column(db.Integer, default=0)
 957 |     requests_today = db.Column(db.Integer, default=0)
 958 |     requests_total = db.Column(db.Integer, default=0)
 959 |     rate_window_start = db.Column(db.DateTime)  # when current hour window started
 960 | 
 961 |     # Scoped entitlements (JSON: {"stream": true, "webhook": true, "signal": true})
 962 |     entitlements = db.Column(db.Text, default='{}')
 963 |     # Key scopes (JSON array: ["read", "stream", "webhook"])
 964 |     key_scopes = db.Column(db.Text, default='["read"]')
 965 |     # Key expiry (NULL = no expiry)
 966 |     key_expires_at = db.Column(db.DateTime, nullable=True)
 967 | 
 968 |     # Webhook delivery
 969 |     webhook_url = db.Column(db.String(500))
 970 |     webhook_secret = db.Column(db.String(100))  # HMAC secret
 971 | 
 972 |     # Status
 973 |     is_active = db.Column(db.Boolean, default=True, index=True)
 974 |     subscription_status = db.Column(db.String(30), default='active')  # active|past_due|canceled
 975 |     current_period_end = db.Column(db.DateTime)
 976 | 
 977 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 978 |     last_used_at = db.Column(db.DateTime)
 979 | 
 980 |     def get_entitlements(self):
 981 |         """Return entitlements as dict."""
 982 |         try:
 983 |             return json.loads(self.entitlements or '{}')
 984 |         except (ValueError, TypeError):
 985 |             return {}
 986 | 
 987 |     def has_entitlement(self, feature: str) -> bool:
 988 |         return self.get_entitlements().get(feature, False)
 989 | 
 990 |     def get_scopes(self):
 991 |         try:
 992 |             return json.loads(self.key_scopes or '["read"]')
 993 |         except (ValueError, TypeError):
 994 |             return ['read']
 995 | 
 996 |     def is_key_valid(self):
 997 |         """Check key is active and not expired."""
 998 |         if not self.is_active:
 999 |             return False
1000 |         if self.subscription_status == 'canceled':
1001 |             return False
1002 |         if self.key_expires_at and datetime.utcnow() > self.key_expires_at:
1003 |             return False
1004 |         return True
1005 | 
1006 | 
1007 | class ApiRequestLog(db.Model):
1008 |     """Per-request log for rate limiting and usage analytics."""
1009 |     __tablename__ = 'api_request_log'
1010 |     __table_args__ = (
1011 |         db.Index('idx_api_log_key_time', 'api_key', 'created_at'),
1012 |     )
1013 | 
1014 |     id = db.Column(db.Integer, primary_key=True)
1015 |     api_key = db.Column(db.String(64), nullable=False)
1016 |     endpoint = db.Column(db.String(200), nullable=False)
1017 |     response_time_ms = db.Column(db.Integer)
1018 |     status_code = db.Column(db.Integer)
1019 |     ip_hash = db.Column(db.String(64))
1020 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
```

### File: core/routes_premium_api.py (847 lines)
```
   1 | """
   2 | routes_premium_api.py — Protocol Pulse Terminal API Blueprint
   3 | Handles: Terminal API endpoints, Stripe checkout for API subscriptions,
   4 |          subscriber dashboard, API playground, webhook delivery.
   5 | 
   6 | Blueprint prefix: (none — registered at root)
   7 | """
   8 | 
   9 | import hashlib
  10 | import hmac
  11 | import json
  12 | import logging
  13 | import os
  14 | import threading
  15 | import time
  16 | import uuid
  17 | from datetime import datetime, timedelta
  18 | from functools import wraps
  19 | 
  20 | import requests as http_requests
  21 | from flask import (
  22 |     Blueprint, Response, jsonify, redirect, render_template,
  23 |     request, stream_with_context, url_for
  24 | )
  25 | 
  26 | from app import db
  27 | import models
  28 | from services.api_key_service import (
  29 |     require_api_key,
  30 |     generate_api_key,
  31 |     generate_webhook_secret,
  32 |     provision_demo_key,
  33 |     get_hourly_usage_sparkline,
  34 |     TIER_ENTITLEMENTS,
  35 | )
  36 | from services.stripe_service import (
  37 |     validate_webhook_signature,
  38 |     provision_terminal_subscriber,
  39 |     cancel_terminal_subscriber,
  40 | )
  41 | 
  42 | logger = logging.getLogger("PremiumAPI")
  43 | 
  44 | premium_api = Blueprint("premium_api", __name__)
  45 | 
  46 | DEMO_KEY = "pp_demo_00000000000000000000000000000001"
  47 | 
  48 | # ─── Helpers ──────────────────────────────────────────────────
  49 | 
  50 | 
  51 | def _send_welcome_email(email: str, api_key: str) -> bool:
  52 |     """Send welcome email with API key via Resend. Returns True on success."""
  53 |     resend_key = os.environ.get("RESEND_API_KEY", "")
  54 |     if not resend_key:
  55 |         logger.warning("RESEND_API_KEY not set — skipping welcome email for %s", email)
  56 |         return False
  57 |     try:
  58 |         resp = http_requests.post(
  59 |             "https://api.resend.com/emails",
  60 |             headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
  61 |             json={
  62 |                 "from": "Protocol Pulse <noreply@protocolpulse.io>",
  63 |                 "to": [email],
  64 |                 "subject": "Your Protocol Pulse Commander API Key",
  65 |                 "html": f"""
  66 | <div style="background:#0a0a0f;color:#eef2ff;font-family:JetBrains Mono,monospace;padding:40px;max-width:600px;margin:0 auto;">
  67 |   <div style="border-bottom:2px solid #f8c15c;padding-bottom:20px;margin-bottom:30px;">
  68 |     <h1 style="color:#f8c15c;font-size:18px;letter-spacing:0.1em;margin:0;">PROTOCOL PULSE</h1>
  69 |     <p style="color:#95a0ba;font-size:12px;margin:4px 0 0;">COMMANDER TERMINAL API</p>
  70 |   </div>
  71 |   <h2 style="color:#eef2ff;font-size:20px;">Your API Key Is Ready</h2>
  72 |   <p style="color:#95a0ba;">Welcome to the Protocol Pulse Commander Tier. Your API key grants access to real-time Bitcoin intelligence data.</p>
  73 |   <div style="background:#1a1a2e;border:1px solid rgba(248,193,92,0.3);border-radius:8px;padding:20px;margin:24px 0;">
  74 |     <p style="color:#95a0ba;font-size:11px;margin:0 0 8px;letter-spacing:0.15em;">YOUR API KEY</p>
  75 |     <code style="color:#f8c15c;font-size:13px;word-break:break-all;">{api_key}</code>
  76 |   </div>
  77 |   <p style="color:#95a0ba;font-size:13px;">Usage: <code style="color:#eef2ff;">X-API-Key: {api_key}</code></p>
  78 |   <p style="color:#95a0ba;font-size:13px;">Rate limit: 1,000 requests/hour | <a href="https://protocolpulse.io/api/dashboard" style="color:#f8c15c;">Manage your key →</a></p>
  79 |   <div style="margin-top:30px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.1);">
  80 |     <p style="color:#95a0ba;font-size:11px;">Quick start:</p>
  81 |     <pre style="background:#0d1118;border:1px solid rgba(255,255,255,0.08);border-radius:6px;padding:12px;font-size:12px;color:#5de4ff;overflow-x:auto;">curl https://protocolpulse.io/api/v2/terminal/topics \\
  82 |   -H "X-API-Key: {api_key}"</pre>
  83 |   </div>
  84 |   <p style="color:#95a0ba;font-size:11px;margin-top:30px;">
  85 |     <a href="https://protocolpulse.io/api/playground" style="color:#f8c15c;">Try the Playground</a> ·
  86 |     <a href="https://protocolpulse.io/api/dashboard" style="color:#f8c15c;">Dashboard</a>
  87 |   </p>
  88 | </div>
  89 | """,
  90 |             },
  91 |             timeout=10,
  92 |         )
  93 |         if resp.status_code in (200, 201):
  94 |             logger.info("Welcome email sent to %s", email)
  95 |             return True
  96 |         logger.warning("Resend returned %d for %s: %s", resp.status_code, email, resp.text[:200])
  97 |         return False
  98 |     except Exception as e:
  99 |         logger.error("Welcome email failed for %s: %s", email, e)
 100 |         return False
 101 | 
 102 | 
 103 | def _json_meta(subscriber) -> dict:
 104 |     """Build the standard meta block for API responses."""
 105 |     from services.api_key_service import TIER_LIMITS
 106 |     limit = TIER_LIMITS.get(subscriber.tier, 1000)
 107 |     # Count requests in last hour from log
 108 |     try:
 109 |         window = datetime.utcnow() - timedelta(hours=1)
 110 |         used = db.session.query(db.func.count(models.ApiRequestLog.id)).filter(
 111 |             models.ApiRequestLog.api_key == subscriber.api_key,
 112 |             models.ApiRequestLog.created_at >= window,
 113 |         ).scalar() or 0
 114 |     except Exception:
 115 |         used = 0
 116 |     return {
 117 |         "tier": subscriber.tier,
 118 |         "requests_this_hour": used,
 119 |         "requests_remaining": max(0, limit - used) if limit != -1 else 999999,
 120 |         "rate_limit": limit,
 121 |         "timestamp": datetime.utcnow().isoformat() + "Z",
 122 |     }
 123 | 
 124 | 
 125 | def _get_topics_data() -> list:
 126 |     """Extract top 20 topics from recent articles."""
 127 |     try:
 128 |         cutoff = datetime.utcnow() - timedelta(hours=24)
 129 |         articles = models.Article.query.filter(
 130 |             models.Article.published.is_(True),
 131 |             models.Article.created_at >= cutoff,
 132 |         ).order_by(models.Article.created_at.desc()).limit(100).all()
 133 | 
 134 |         topic_counts: dict = {}
 135 |         for art in articles:
 136 |             tags_raw = art.tags or ""
 137 |             if tags_raw.startswith("["):
 138 |                 try:
 139 |                     tags = json.loads(tags_raw)
 140 |                 except Exception:
 141 |                     tags = []
 142 |             else:
 143 |                 tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
 144 |             for tag in tags:
 145 |                 tag_clean = tag.strip().lower()
 146 |                 if tag_clean:
 147 |                     topic_counts[tag_clean] = topic_counts.get(tag_clean, 0) + 1
 148 | 
 149 |         sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:20]
 150 |         return [{"topic": t, "mentions": c, "trend": "rising" if c > 3 else "stable"}
 151 |                 for t, c in sorted_topics]
 152 |     except Exception as e:
 153 |         logger.warning("topics data error: %s", e)
 154 |         return [{"topic": "bitcoin", "mentions": 10, "trend": "rising"},
 155 |                 {"topic": "halving", "mentions": 7, "trend": "stable"}]
 156 | 
 157 | 
 158 | def _get_entities_data() -> dict:
 159 |     """Extract named entities from recent article tags/content."""
 160 |     try:
 161 |         cutoff = datetime.utcnow() - timedelta(hours=24)
 162 |         articles = models.Article.query.filter(
 163 |             models.Article.published.is_(True),
 164 |             models.Article.created_at >= cutoff,
 165 |         ).limit(50).all()
 166 | 
 167 |         people, orgs, coins = {}, {}, {}
 168 |         coin_keywords = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "lightning"]
 169 |         people_keywords = ["saylor", "musk", "gensler", "warren", "yellen", "powell"]
 170 |         org_keywords = ["fed", "sec", "coinbase", "grayscale", "blackrock", "microstrategy", "galaxy"]
 171 | 
 172 |         for art in articles:
 173 |             text = (art.title + " " + (art.summary or "")).lower()
 174 |             for kw in coin_keywords:
 175 |                 if kw in text:
 176 |                     coins[kw] = coins.get(kw, 0) + 1
 177 |             for kw in people_keywords:
 178 |                 if kw in text:
 179 |                     people[kw] = people.get(kw, 0) + 1
 180 |             for kw in org_keywords:
 181 |                 if kw in text:
 182 |                     orgs[kw] = orgs.get(kw, 0) + 1
 183 | 
 184 |         return {
 185 |             "people": [{"name": k, "mentions": v} for k, v in sorted(people.items(), key=lambda x: -x[1])[:10]],
 186 |             "organizations": [{"name": k, "mentions": v} for k, v in sorted(orgs.items(), key=lambda x: -x[1])[:10]],
 187 |             "coins": [{"symbol": k.upper(), "mentions": v} for k, v in sorted(coins.items(), key=lambda x: -x[1])[:5]],
 188 |         }
 189 |     except Exception as e:
 190 |         logger.warning("entities data error: %s", e)
 191 |         return {"people": [], "organizations": [], "coins": [{"symbol": "BTC", "mentions": 20}]}
 192 | 
 193 | 
 194 | def _get_sentiment_data() -> dict:
 195 |     """Return latest sentiment from SentimentSnapshot or fallback."""
 196 |     try:
 197 |         snap = models.SentimentSnapshot.query.order_by(
 198 |             models.SentimentSnapshot.computed_at.desc()
 199 |         ).first()
 200 |         if snap:
 201 |             top_kw = []
 202 |             if snap.top_keywords:
 203 |                 try:
 204 |                     top_kw = json.loads(snap.top_keywords)
 205 |                 except Exception:
 206 |                     top_kw = snap.top_keywords.split(",")[:5] if snap.top_keywords else []
 207 |             return {
 208 |                 "score": round(snap.score, 1),
 209 |                 "state": snap.state or "NEUTRAL",
 210 |                 "label": snap.state_label or "Neutral",
 211 |                 "velocity": round(snap.velocity or 0, 2),
 212 |                 "top_keywords": top_kw[:5],
 213 |                 "sample_size": snap.sample_size or 0,
 214 |                 "computed_at": snap.computed_at.isoformat() + "Z" if snap.computed_at else None,
 215 |             }
 216 |     except Exception as e:
 217 |         logger.warning("sentiment data error: %s", e)
 218 |     return {"score": 52.0, "state": "NEUTRAL", "label": "Neutral", "velocity": 0.0,
 219 |             "top_keywords": ["bitcoin", "network"], "sample_size": 0, "computed_at": None}
 220 | 
 221 | 
 222 | def _get_breaking_data() -> list:
 223 |     """Articles published in last 2 hours."""
 224 |     try:
 225 |         cutoff = datetime.utcnow() - timedelta(hours=2)
 226 |         articles = models.Article.query.filter(
 227 |             models.Article.published.is_(True),
 228 |             models.Article.created_at >= cutoff,
 229 |         ).order_by(models.Article.created_at.desc()).limit(10).all()
 230 |         return [{
 231 |             "id": a.id,
 232 |             "title": a.title,
 233 |             "summary": (a.summary or "")[:300],
 234 |             "category": a.category or "bitcoin",
 235 |             "url": f"/articles/{a.id}",
 236 |             "published_at": a.created_at.isoformat() + "Z" if a.created_at else None,
 237 |         } for a in articles]
 238 |     except Exception as e:
 239 |         logger.warning("breaking data error: %s", e)
 240 |         return []
 241 | 
 242 | 
 243 | def _get_signal_data() -> dict:
 244 |     """Compute composite Signal Strength 0-100."""
 245 |     try:
 246 |         sentiment = _get_sentiment_data()
 247 |         breaking = _get_breaking_data()
 248 |         topics = _get_topics_data()
 249 | 
 250 |         sentiment_score = float(sentiment.get("score", 50))
 251 |         breaking_score = min(100, len(breaking) * 12)  # up to ~8 articles = 100
 252 |         topic_score = min(100, len(topics) * 5)
 253 |         velocity_bonus = min(20, abs(float(sentiment.get("velocity", 0))) * 10)
 254 | 
 255 |         composite = (sentiment_score * 0.4 + breaking_score * 0.3 + topic_score * 0.2 + velocity_bonus * 0.1)
 256 |         composite = round(min(100, max(0, composite)), 1)
 257 | 
 258 |         state = "EXTREME FEAR" if composite < 20 else \
 259 |                 "FEAR" if composite < 40 else \
 260 |                 "NEUTRAL" if composite < 60 else \
 261 |                 "GREED" if composite < 80 else "EXTREME GREED"
 262 | 
 263 |         return {
 264 |             "composite_score": composite,
 265 |             "state": state,
 266 |             "components": {
 267 |                 "sentiment": round(sentiment_score, 1),
 268 |                 "breaking_activity": round(breaking_score, 1),
 269 |                 "topic_velocity": round(topic_score, 1),
 270 |                 "momentum_bonus": round(velocity_bonus, 1),
 271 |             },
 272 |             "timestamp": datetime.utcnow().isoformat() + "Z",
 273 |         }
 274 |     except Exception as e:
 275 |         logger.warning("signal data error: %s", e)
 276 |         return {"composite_score": 50.0, "state": "NEUTRAL", "components": {},
 277 |                 "timestamp": datetime.utcnow().isoformat() + "Z"}
 278 | 
 279 | 
 280 | # ─── Terminal API Endpoints ────────────────────────────────────
 281 | 
 282 | 
 283 | @premium_api.route("/api/v2/terminal/topics", methods=["GET"])
 284 | @require_api_key
 285 | def terminal_topics(_subscriber=None):
 286 |     data = _get_topics_data()
 287 |     return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200
 288 | 
 289 | 
 290 | @premium_api.route("/api/v2/terminal/entities", methods=["GET"])
 291 | @require_api_key
 292 | def terminal_entities(_subscriber=None):
 293 |     data = _get_entities_data()
 294 |     return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200
 295 | 
 296 | 
 297 | @premium_api.route("/api/v2/terminal/sentiment", methods=["GET"])
 298 | @require_api_key
 299 | def terminal_sentiment(_subscriber=None):
 300 |     data = _get_sentiment_data()
 301 |     return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200
 302 | 
 303 | 
 304 | @premium_api.route("/api/v2/terminal/breaking", methods=["GET"])
 305 | @require_api_key
 306 | def terminal_breaking(_subscriber=None):
 307 |     data = _get_breaking_data()
 308 |     return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200
 309 | 
 310 | 
 311 | @premium_api.route("/api/v2/terminal/signal", methods=["GET"])
 312 | @require_api_key
 313 | def terminal_signal(_subscriber=None):
 314 |     data = _get_signal_data()
 315 |     return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200
 316 | 
 317 | 
 318 | @premium_api.route("/api/v2/terminal/status", methods=["GET"])
 319 | @require_api_key
 320 | def terminal_status(_subscriber=None):
 321 |     """Subscriber usage stats and quota."""
 322 |     sparkline = get_hourly_usage_sparkline(_subscriber.api_key, db, models)
 323 |     data = {
 324 |         "email": _subscriber.email,
 325 |         "tier": _subscriber.tier,
 326 |         "api_key_prefix": _subscriber.api_key[:12] + "...",
 327 |         "requests_total": _subscriber.requests_total or 0,
 328 |         "rate_limit_per_hour": _subscriber.rate_limit_per_hour,
 329 |         "subscription_status": _subscriber.subscription_status,
 330 |         "current_period_end": _subscriber.current_period_end.isoformat() + "Z"
 331 |             if _subscriber.current_period_end else None,
 332 |         "created_at": _subscriber.created_at.isoformat() + "Z" if _subscriber.created_at else None,
 333 |         "last_used_at": _subscriber.last_used_at.isoformat() + "Z" if _subscriber.last_used_at else None,
 334 |         "entitlements": _subscriber.get_entitlements(),
 335 |         "hourly_sparkline": sparkline,
 336 |     }
 337 |     return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200
 338 | 
 339 | 
 340 | @premium_api.route("/api/v2/terminal/stream", methods=["GET"])
 341 | @require_api_key
 342 | def terminal_stream(_subscriber=None):
 343 |     """SSE stream of breaking news. Commander only (entitlement: stream)."""
 344 |     channel = request.args.get("channel", "all")  # breaking|sentiment|all
 345 | 
 346 |     def generate():
 347 |         """SSE generator — polls for new articles every 15s."""
 348 |         last_article_id = None
 349 |         try:
 350 |             latest = models.Article.query.filter_by(published=True).order_by(
 351 |                 models.Article.created_at.desc()
 352 |             ).first()
 353 |             if latest:
 354 |                 last_article_id = latest.id
 355 |         except Exception:
 356 |             pass
 357 | 
 358 |         yield f"data: {json.dumps({'type': 'connected', 'channel': channel, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
 359 | 
 360 |         heartbeat_counter = 0
 361 |         while True:
 362 |             time.sleep(15)
 363 |             heartbeat_counter += 1
 364 | 
 365 |             try:
 366 |                 # Check for new breaking articles
 367 |                 if channel in ("breaking", "all"):
 368 |                     query = models.Article.query.filter(
 369 |                         models.Article.published.is_(True),
 370 |                     ).order_by(models.Article.created_at.desc()).limit(5)
 371 | 
 372 |                     new_articles = []
 373 |                     for art in query.all():
 374 |                         if last_article_id is None or art.id > last_article_id:
 375 |                             new_articles.append(art)
 376 |                             if last_article_id is None or art.id > last_article_id:
 377 |                                 last_article_id = art.id
 378 | 
 379 |                     for art in new_articles:
 380 |                         payload = {
 381 |                             "type": "breaking_article",
 382 |                             "data": {
 383 |                                 "id": art.id,
 384 |                                 "title": art.title,
 385 |                                 "summary": (art.summary or "")[:200],
 386 |                                 "category": art.category or "bitcoin",
 387 |                                 "url": f"/articles/{art.id}",
 388 |                                 "published_at": art.created_at.isoformat() + "Z" if art.created_at else None,
 389 |                             },
 390 |                             "timestamp": datetime.utcnow().isoformat(),
 391 |                         }
 392 |                         yield f"data: {json.dumps(payload)}\n\n"
 393 | 
 394 |                 # Check for sentiment updates
 395 |                 if channel in ("sentiment", "all") and heartbeat_counter % 4 == 0:  # every ~60s
 396 |                     sentiment = _get_sentiment_data()
 397 |                     payload = {
 398 |                         "type": "sentiment_update",
 399 |                         "data": sentiment,
 400 |                         "timestamp": datetime.utcnow().isoformat(),
 401 |                     }
 402 |                     yield f"data: {json.dumps(payload)}\n\n"
 403 | 
 404 |                 # Heartbeat
 405 |                 yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
 406 | 
 407 |             except GeneratorExit:
 408 |                 return
 409 |             except Exception as e:
 410 |                 logger.warning("SSE stream error: %s", e)
 411 |                 yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error — reconnecting'})}\n\n"
 412 |                 time.sleep(5)
 413 | 
 414 |     return Response(
 415 |         stream_with_context(generate()),
 416 |         mimetype="text/event-stream",
 417 |         headers={
 418 |             "Cache-Control": "no-cache",
 419 |             "X-Accel-Buffering": "no",
 420 |             "Connection": "keep-alive",
 421 |         },
 422 |     )
 423 | 
 424 | 
 425 | @premium_api.route("/api/v2/terminal/docs", methods=["GET"])
 426 | def terminal_docs():
 427 |     """OpenAPI-style documentation (public)."""
 428 |     docs = {
 429 |         "title": "Protocol Pulse Terminal API",
 430 |         "version": "2.0",
 431 |         "base_url": "https://protocolpulse.io",
 432 |         "auth": {
 433 |             "type": "API Key",
 434 |             "header": "X-API-Key",
 435 |             "example": "X-API-Key: pp_cmd_your_key_here",
 436 |         },
 437 |         "endpoints": [
 438 |             {"method": "GET", "path": "/api/v2/terminal/topics", "description": "Top 20 trending topics (last 24h)", "tier": "all"},
 439 |             {"method": "GET", "path": "/api/v2/terminal/entities", "description": "Named entities: people, orgs, coins", "tier": "commander+"},
 440 |             {"method": "GET", "path": "/api/v2/terminal/sentiment", "description": "Aggregate sentiment score + components", "tier": "all"},
 441 |             {"method": "GET", "path": "/api/v2/terminal/breaking", "description": "Articles published in last 2 hours", "tier": "all"},
 442 |             {"method": "GET", "path": "/api/v2/terminal/signal", "description": "Composite Signal Strength 0-100", "tier": "commander+"},
 443 |             {"method": "GET", "path": "/api/v2/terminal/status", "description": "Your usage stats and quota", "tier": "all"},
 444 |             {"method": "GET", "path": "/api/v2/terminal/stream", "description": "SSE breaking news stream", "tier": "commander"},
 445 |         ],
 446 |         "rate_limits": {
 447 |             "demo": "20 requests/hour",
 448 |             "commander": "1,000 requests/hour",
 449 |             "enterprise": "Unlimited",
 450 |         },
 451 |         "get_key": "https://protocolpulse.io/premium",
 452 |     }
 453 |     return jsonify(docs), 200
 454 | 
 455 | 
 456 | # ─── Stripe Checkout ──────────────────────────────────────────
 457 | 
 458 | 
 459 | @premium_api.route("/api/v2/terminal/subscribe", methods=["POST"])
 460 | def terminal_subscribe():
 461 |     """Create Stripe Checkout session for Terminal API subscription."""
 462 |     try:
 463 |         import stripe
 464 |     except ImportError:
 465 |         return jsonify({"error": "Stripe not installed. Run: pip install stripe"}), 500
 466 | 
 467 |     data = request.get_json(silent=True) or {}
 468 |     email = (data.get("email") or "").strip()
 469 | 
 470 |     if not email or "@" not in email:
 471 |         return jsonify({"error": "Valid email required"}), 400
 472 | 
 473 |     stripe_key = os.environ.get("STRIPE_SECRET_KEY")
 474 |     if not stripe_key:
 475 |         return jsonify({
 476 |             "error": "Stripe not configured. Contact support@protocolpulse.io",
 477 |             "code": "STRIPE_NOT_CONFIGURED"
 478 |         }), 503
 479 | 
 480 |     price_id = os.environ.get("STRIPE_COMMANDER_PRICE_ID")
 481 |     if not price_id:
 482 |         return jsonify({
 483 |             "error": "Product not configured. Contact support@protocolpulse.io",
 484 |             "code": "PRICE_NOT_CONFIGURED"
 485 |         }), 503
 486 | 
 487 |     try:
 488 |         stripe.api_key = stripe_key
 489 |         session = stripe.checkout.Session.create(
 490 |             payment_method_types=["card"],
 491 |             mode="subscription",
 492 |             customer_email=email,
 493 |             line_items=[{"price": price_id, "quantity": 1}],
 494 |             success_url=request.url_root.rstrip("/") + "/subscribe/terminal/success?session_id={CHECKOUT_SESSION_ID}",
 495 |             cancel_url=request.url_root.rstrip("/") + "/premium",
 496 |             metadata={
 497 |                 "subscription_type": "terminal_api",
 498 |                 "tier": "commander",
 499 |                 "email": email,
 500 |             },
 501 |         )
 502 |         return jsonify({"checkout_url": session.url, "session_id": session.id}), 200
 503 |     except Exception as e:
 504 |         logger.error("Stripe checkout error: %s", e)
 505 |         return jsonify({"error": "Checkout failed. Please try again.", "detail": str(e)[:200]}), 500
 506 | 
 507 | 
 508 | @premium_api.route("/subscribe/terminal/success", methods=["GET"])
 509 | def terminal_subscribe_success():
 510 |     """Post-Stripe success page — shows API key."""
 511 |     session_id = request.args.get("session_id", "")
 512 |     api_key = None
 513 |     email = None
 514 |     error = None
 515 | 
 516 |     if session_id:
 517 |         try:
 518 |             import stripe
 519 |             stripe_key = os.environ.get("STRIPE_SECRET_KEY")
 520 |             if stripe_key:
 521 |                 stripe.api_key = stripe_key
 522 |                 checkout_session = stripe.checkout.Session.retrieve(
 523 |                     session_id,
 524 |                     expand=["customer"],
 525 |                 )
 526 |                 customer_email = (checkout_session.get("customer_details") or {}).get("email")
 527 |                 if customer_email:
 528 |                     email = customer_email
 529 |                     # Look up subscriber
 530 |                     sub = models.ApiSubscriber.query.filter_by(email=customer_email).first()
 531 |                     if sub:
 532 |                         api_key = sub.api_key
 533 |                     else:
 534 |                         # Trigger provisioning (webhook may not have fired yet)
 535 |                         result = provision_terminal_subscriber(dict(checkout_session), db, models)
 536 |                         if result["success"]:
 537 |                             api_key = result["api_key"]
 538 |                             _send_welcome_email(customer_email, api_key)
 539 |         except Exception as e:
 540 |             logger.error("Success page error for session %s: %s", session_id, e)
 541 |             error = "Could not retrieve your subscription details. Check your email for your API key."
 542 | 
 543 |     return render_template(
 544 |         "subscribe_terminal_success.html",
 545 |         api_key=api_key,
 546 |         email=email,
 547 |         error=error,
 548 |         session_id=session_id,
 549 |     )
 550 | 
 551 | 
 552 | @premium_api.route("/webhook/stripe/terminal", methods=["POST"])
 553 | def terminal_stripe_webhook():
 554 |     """Stripe webhook handler for Terminal API subscriptions only."""
 555 |     payload = request.get_data()
 556 |     sig_header = request.headers.get("Stripe-Signature", "")
 557 |     webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
 558 | 
 559 |     if not webhook_secret:
 560 |         logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature validation")
 561 |         try:
 562 |             event = json.loads(payload)
 563 |         except Exception:
 564 |             return jsonify({"error": "Invalid payload"}), 400
 565 |     else:
 566 |         event = validate_webhook_signature(payload, sig_header, webhook_secret)
 567 |         if not event:
 568 |             logger.warning("Invalid Stripe webhook signature from %s", request.remote_addr)
 569 |             return jsonify({"error": "Invalid signature"}), 400
 570 | 
 571 |     event_type = event.get("type", "")
 572 |     event_obj = (event.get("data") or {}).get("object", {})
 573 | 
 574 |     logger.info("Terminal webhook: %s", event_type)
 575 | 
 576 |     try:
 577 |         if event_type == "checkout.session.completed":
 578 |             result = provision_terminal_subscriber(event_obj, db, models)
 579 |             if result["success"] and result.get("api_key") and result.get("email"):
 580 |                 # Send welcome email in background thread
 581 |                 email = result["email"]
 582 |                 key = result["api_key"]
 583 |                 t = threading.Thread(target=_send_welcome_email, args=(email, key), daemon=True)
 584 |                 t.start()
 585 | 
 586 |         elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
 587 |             if event_type == "customer.subscription.deleted":
 588 |                 cancel_terminal_subscriber(event_obj, db, models)
 589 |             elif event_type == "customer.subscription.updated":
 590 |                 status = event_obj.get("status")
 591 |                 sub_id = event_obj.get("id")
 592 |                 if status and sub_id:
 593 |                     try:
 594 |                         sub = models.ApiSubscriber.query.filter_by(
 595 |                             stripe_subscription_id=sub_id
 596 |                         ).first()
 597 |                         if sub:
 598 |                             sub.subscription_status = status
 599 |                             if status == "active":
 600 |                                 sub.is_active = True
 601 |                             elif status in ("canceled", "unpaid"):
 602 |                                 sub.is_active = False
 603 |                             db.session.commit()
 604 |                     except Exception as e:
 605 |                         logger.error("Error updating subscription status: %s", e)
 606 |                         db.session.rollback()
 607 | 
 608 |         elif event_type == "invoice.payment_failed":
 609 |             customer_id = event_obj.get("customer")
 610 |             if customer_id:
 611 |                 try:
 612 |                     sub = models.ApiSubscriber.query.filter_by(
 613 |                         stripe_customer_id=customer_id
 614 |                     ).first()
 615 |                     if sub:
 616 |                         sub.subscription_status = "past_due"
 617 |                         db.session.commit()
 618 |                 except Exception as e:
 619 |                     logger.error("Error marking past_due: %s", e)
 620 |                     db.session.rollback()
 621 | 
 622 |     except Exception as e:
 623 |         logger.error("Webhook handler error for %s: %s", event_type, e)
 624 | 
 625 |     return jsonify({"received": True}), 200
 626 | 
 627 | 
 628 | # ─── Dashboard ────────────────────────────────────────────────
 629 | 
 630 | 
 631 | @premium_api.route("/api/dashboard", methods=["GET"])
 632 | def api_dashboard():
 633 |     """Subscriber self-service dashboard. Auth via X-API-Key header or ?key= param."""
 634 |     api_key = (
 635 |         request.headers.get("X-API-Key", "")
 636 |         or request.args.get("key", "")
 637 |         or ""
 638 |     ).strip()
 639 | 
 640 |     subscriber = None
 641 |     if api_key:
 642 |         try:
 643 |             subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
 644 |         except Exception as e:
 645 |             logger.error("Dashboard DB error: %s", e)
 646 | 
 647 |     if not subscriber or api_key == DEMO_KEY:
 648 |         subscriber = None  # Show unauthenticated state
 649 | 
 650 |     sparkline = []
 651 |     if subscriber:
 652 |         sparkline = get_hourly_usage_sparkline(subscriber.api_key, db, models)
 653 | 
 654 |     return render_template(
 655 |         "api_dashboard.html",
 656 |         subscriber=subscriber,
 657 |         sparkline_json=json.dumps(sparkline),
 658 |         api_key=api_key if subscriber else "",
 659 |     )
 660 | 
 661 | 
 662 | @premium_api.route("/api/dashboard/rotate-key", methods=["POST"])
 663 | def rotate_api_key():
 664 |     """Generate a new API key, deactivate the old one (1hr grace period)."""
 665 |     api_key = request.headers.get("X-API-Key", "").strip()
 666 |     if not api_key:
 667 |         return jsonify({"error": "X-API-Key header required"}), 401
 668 | 
 669 |     try:
 670 |         subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
 671 |         if not subscriber or not subscriber.is_key_valid():
 672 |             return jsonify({"error": "Invalid or expired API key"}), 401
 673 | 
 674 |         if subscriber.tier == "demo":
 675 |             return jsonify({"error": "Cannot rotate demo key"}), 403
 676 | 
 677 |         new_key = generate_api_key(subscriber.tier)
 678 |         old_key = subscriber.api_key
 679 |         subscriber.api_key = new_key
 680 |         # Set old key expiry (1hr grace — handled by is_key_valid checking key_expires_at)
 681 |         # We just replace the key; old key is gone from DB immediately
 682 |         db.session.commit()
 683 | 
 684 |         logger.info("API key rotated for %s", subscriber.email)
 685 |         return jsonify({
 686 |             "success": True,
 687 |             "new_api_key": new_key,
 688 |             "message": "Old key is immediately invalidated. Update your applications.",
 689 |         }), 200
 690 |     except Exception as e:
 691 |         logger.error("Key rotation error: %s", e)
 692 |         db.session.rollback()
 693 |         return jsonify({"error": "Key rotation failed. Try again."}), 500
 694 | 
 695 | 
 696 | @premium_api.route("/api/dashboard/billing-portal", methods=["POST"])
 697 | def billing_portal():
 698 |     """Create Stripe Customer Portal session."""
 699 |     api_key = request.headers.get("X-API-Key", "").strip()
 700 |     if not api_key:
 701 |         return jsonify({"error": "X-API-Key header required"}), 401
 702 | 
 703 |     try:
 704 |         subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
 705 |         if not subscriber:
 706 |             return jsonify({"error": "Invalid API key"}), 401
 707 |     except Exception as e:
 708 |         return jsonify({"error": "Service error"}), 503
 709 | 
 710 |     stripe_key = os.environ.get("STRIPE_SECRET_KEY")
 711 |     if not stripe_key or not subscriber.stripe_customer_id:
 712 |         return jsonify({
 713 |             "error": "Billing portal not available. Email: support@protocolpulse.io",
 714 |             "code": "NOT_CONFIGURED"
 715 |         }), 503
 716 | 
 717 |     try:
 718 |         import stripe
 719 |         stripe.api_key = stripe_key
 720 |         portal = stripe.billing_portal.Session.create(
 721 |             customer=subscriber.stripe_customer_id,
 722 |             return_url=request.url_root.rstrip("/") + "/api/dashboard",
 723 |         )
 724 |         return jsonify({"portal_url": portal.url}), 200
 725 |     except Exception as e:
 726 |         logger.error("Billing portal error: %s", e)
 727 |         return jsonify({"error": "Could not open billing portal. Try again."}), 500
 728 | 
 729 | 
 730 | @premium_api.route("/api/dashboard/webhook", methods=["POST"])
 731 | def configure_webhook():
 732 |     """Configure subscriber webhook URL."""
 733 |     api_key = request.headers.get("X-API-Key", "").strip()
 734 |     if not api_key:
 735 |         return jsonify({"error": "X-API-Key header required"}), 401
 736 | 
 737 |     data = request.get_json(silent=True) or {}
 738 |     webhook_url = (data.get("webhook_url") or "").strip()
 739 | 
 740 |     try:
 741 |         subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
 742 |         if not subscriber or not subscriber.is_key_valid():
 743 |             return jsonify({"error": "Invalid or expired API key"}), 401
 744 | 
 745 |         if not subscriber.has_entitlement("webhook"):
 746 |             return jsonify({"error": "Webhook delivery requires Commander tier", "upgrade_url": "/premium"}), 403
 747 | 
 748 |         if webhook_url and not webhook_url.startswith("https://"):
 749 |             return jsonify({"error": "Webhook URL must use HTTPS"}), 400
 750 | 
 751 |         subscriber.webhook_url = webhook_url or None
 752 |         if webhook_url and not subscriber.webhook_secret:
 753 |             subscriber.webhook_secret = generate_webhook_secret()
 754 |         db.session.commit()
 755 | 
 756 |         return jsonify({
 757 |             "success": True,
 758 |             "webhook_url": subscriber.webhook_url,
 759 |             "webhook_secret": subscriber.webhook_secret,
 760 |             "message": "Webhook configured. Sign each payload with HMAC-SHA256.",
 761 |         }), 200
 762 |     except Exception as e:
 763 |         logger.error("Webhook config error: %s", e)
 764 |         db.session.rollback()
 765 |         return jsonify({"error": "Failed to configure webhook"}), 500
 766 | 
 767 | 
 768 | # ─── API Playground ───────────────────────────────────────────
 769 | 
 770 | 
 771 | @premium_api.route("/api/playground", methods=["GET"])
 772 | def api_playground():
 773 |     """Interactive API playground with demo key."""
 774 |     demo_key = DEMO_KEY
 775 |     return render_template("api_playground.html", demo_key=demo_key)
 776 | 
 777 | 
 778 | # ─── Webhook Delivery (background) ───────────────────────────
 779 | 
 780 | 
 781 | def _deliver_webhook(subscriber: models.ApiSubscriber, payload: dict):
 782 |     """Deliver a webhook payload to a subscriber. Retries 3x with exponential backoff."""
 783 |     if not subscriber.webhook_url or not subscriber.webhook_secret:
 784 |         return
 785 | 
 786 |     body = json.dumps(payload)
 787 |     sig = hmac.new(
 788 |         subscriber.webhook_secret.encode(),
 789 |         body.encode(),
 790 |         hashlib.sha256,
 791 |     ).hexdigest()
 792 | 
 793 |     for attempt in range(3):
 794 |         try:
 795 |             resp = http_requests.post(
 796 |                 subscriber.webhook_url,
 797 |                 data=body,
 798 |                 headers={
 799 |                     "Content-Type": "application/json",
 800 |                     "X-PP-Signature": f"sha256={sig}",
 801 |                     "X-PP-Event": payload.get("event", "unknown"),
 802 |                 },
 803 |                 timeout=10,
 804 |             )
 805 |             if resp.status_code < 300:
 806 |                 logger.info("Webhook delivered to %s (attempt %d)", subscriber.webhook_url, attempt + 1)
 807 |                 return
 808 |             logger.warning("Webhook %s returned %d (attempt %d)", subscriber.webhook_url, resp.status_code, attempt + 1)
 809 |         except Exception as e:
 810 |             logger.warning("Webhook delivery error (attempt %d): %s", attempt + 1, e)
 811 |         time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s
 812 | 
 813 | 
 814 | def deliver_breaking_article_webhooks(article_id: int, title: str, summary: str, url: str, published_at: str):
 815 |     """
 816 |     Deliver breaking article webhook to all subscribers with webhook_url set.
 817 |     Called from article publish routes.
 818 |     """
 819 |     payload = {
 820 |         "event": "breaking_article",
 821 |         "data": {
 822 |             "id": article_id,
 823 |             "title": title,
 824 |             "summary": summary[:300] if summary else "",
 825 |             "url": url,
 826 |             "published_at": published_at,
 827 |         },
 828 |         "timestamp": datetime.utcnow().isoformat() + "Z",
 829 |     }
 830 | 
 831 |     def background():
 832 |         try:
 833 |             from app import app
 834 |             with app.app_context():
 835 |                 subscribers = models.ApiSubscriber.query.filter(
 836 |                     models.ApiSubscriber.webhook_url.isnot(None),
 837 |                     models.ApiSubscriber.is_active.is_(True),
 838 |                 ).all()
 839 |                 for sub in subscribers:
 840 |                     if sub.has_entitlement("webhook"):
 841 |                         _deliver_webhook(sub, payload)
 842 |         except Exception as e:
 843 |             logger.error("Webhook delivery background error: %s", e)
 844 | 
 845 |     t = threading.Thread(target=background, daemon=True)
 846 |     t.start()
 847 | 
```

### File: core/services/api_key_service.py (316 lines)
```
   1 | """
   2 | api_key_service.py — Terminal API authentication middleware, rate limiting, and usage tracking.
   3 | 
   4 | Features:
   5 | - X-API-Key header authentication
   6 | - Sliding window rate limiting (true hourly window)
   7 | - Burst protection (max 50 req/minute)
   8 | - Usage tracking per request
   9 | - Entitlements checking
  10 | """
  11 | 
  12 | import hashlib
  13 | import json
  14 | import logging
  15 | import os
  16 | import time
  17 | import uuid
  18 | from datetime import datetime, timedelta
  19 | from functools import wraps
  20 | 
  21 | from flask import request, jsonify
  22 | 
  23 | logger = logging.getLogger("ApiKeyService")
  24 | 
  25 | # ── Tier defaults ─────────────────────────────────────────────
  26 | 
  27 | TIER_LIMITS = {
  28 |     "demo": 20,
  29 |     "commander": 1000,
  30 |     "enterprise": -1,  # unlimited
  31 | }
  32 | 
  33 | TIER_BURST_LIMITS = {
  34 |     "demo": 5,       # max req/minute
  35 |     "commander": 50,
  36 |     "enterprise": 200,
  37 | }
  38 | 
  39 | TIER_ENTITLEMENTS = {
  40 |     "demo": {
  41 |         "stream": False,
  42 |         "webhook": False,
  43 |         "signal": True,
  44 |         "breaking": True,
  45 |         "topics": True,
  46 |         "entities": False,
  47 |         "sentiment": True,
  48 |     },
  49 |     "commander": {
  50 |         "stream": True,
  51 |         "webhook": True,
  52 |         "signal": True,
  53 |         "breaking": True,
  54 |         "topics": True,
  55 |         "entities": True,
  56 |         "sentiment": True,
  57 |     },
  58 |     "enterprise": {
  59 |         "stream": True,
  60 |         "webhook": True,
  61 |         "signal": True,
  62 |         "breaking": True,
  63 |         "topics": True,
  64 |         "entities": True,
  65 |         "sentiment": True,
  66 |     },
  67 | }
  68 | 
  69 | # Endpoint → entitlement required
  70 | ENDPOINT_ENTITLEMENTS = {
  71 |     "/api/v2/terminal/stream": "stream",
  72 |     "/api/v2/terminal/entities": "entities",
  73 |     "/api/v2/terminal/signal": "signal",
  74 | }
  75 | 
  76 | 
  77 | def generate_api_key(tier: str = "commander") -> str:
  78 |     """Generate a prefixed UUID4 API key. Format: pp_cmd_<32hex>"""
  79 |     prefix_map = {"commander": "pp_cmd_", "enterprise": "pp_ent_", "demo": "pp_demo_"}
  80 |     prefix = prefix_map.get(tier, "pp_cmd_")
  81 |     return prefix + str(uuid.uuid4()).replace("-", "")
  82 | 
  83 | 
  84 | def generate_webhook_secret() -> str:
  85 |     """Generate a random HMAC secret for webhook signing."""
  86 |     return "whs_" + str(uuid.uuid4()).replace("-", "")
  87 | 
  88 | 
  89 | def _hash_ip(ip: str) -> str:
  90 |     return hashlib.sha256(ip.encode()).hexdigest()[:16]
  91 | 
  92 | 
  93 | def check_rate_limit(subscriber, db, models) -> dict:
  94 |     """
  95 |     Sliding window rate limit check.
  96 |     Returns: {"allowed": bool, "remaining": int, "limit": int, "retry_after": int|None}
  97 |     """
  98 |     from models import ApiRequestLog
  99 | 
 100 |     tier = subscriber.tier
 101 |     limit = TIER_LIMITS.get(tier, 20)
 102 | 
 103 |     if limit == -1:  # unlimited
 104 |         return {"allowed": True, "remaining": 999999, "limit": -1, "retry_after": None}
 105 | 
 106 |     # Sliding window: count requests in last 60 minutes
 107 |     window_start = datetime.utcnow() - timedelta(hours=1)
 108 |     count_hour = db.session.query(db.func.count(ApiRequestLog.id)).filter(
 109 |         ApiRequestLog.api_key == subscriber.api_key,
 110 |         ApiRequestLog.created_at >= window_start
 111 |     ).scalar() or 0
 112 | 
 113 |     if count_hour >= limit:
 114 |         # Find oldest request in window to compute Retry-After
 115 |         oldest = db.session.query(ApiRequestLog.created_at).filter(
 116 |             ApiRequestLog.api_key == subscriber.api_key,
 117 |             ApiRequestLog.created_at >= window_start
 118 |         ).order_by(ApiRequestLog.created_at.asc()).first()
 119 |         retry_after = 3600
 120 |         if oldest:
 121 |             elapsed = (datetime.utcnow() - oldest[0]).total_seconds()
 122 |             retry_after = max(1, int(3600 - elapsed))
 123 |         return {"allowed": False, "remaining": 0, "limit": limit, "retry_after": retry_after}
 124 | 
 125 |     # Burst check: count requests in last 60 seconds
 126 |     burst_limit = TIER_BURST_LIMITS.get(tier, 5)
 127 |     burst_window = datetime.utcnow() - timedelta(seconds=60)
 128 |     count_minute = db.session.query(db.func.count(ApiRequestLog.id)).filter(
 129 |         ApiRequestLog.api_key == subscriber.api_key,
 130 |         ApiRequestLog.created_at >= burst_window
 131 |     ).scalar() or 0
 132 | 
 133 |     if count_minute >= burst_limit:
 134 |         return {"allowed": False, "remaining": limit - count_hour, "limit": limit, "retry_after": 60}
 135 | 
 136 |     return {
 137 |         "allowed": True,
 138 |         "remaining": limit - count_hour - 1,
 139 |         "limit": limit,
 140 |         "retry_after": None,
 141 |     }
 142 | 
 143 | 
 144 | def log_request(subscriber, endpoint: str, status_code: int, response_time_ms: int, db, models):
 145 |     """Log a request to api_request_log and update subscriber stats."""
 146 |     from models import ApiRequestLog
 147 | 
 148 |     try:
 149 |         ip = request.remote_addr or "unknown"
 150 |         log_entry = ApiRequestLog(
 151 |             api_key=subscriber.api_key,
 152 |             endpoint=endpoint,
 153 |             response_time_ms=response_time_ms,
 154 |             status_code=status_code,
 155 |             ip_hash=_hash_ip(ip),
 156 |         )
 157 |         db.session.add(log_entry)
 158 | 
 159 |         # Update subscriber totals
 160 |         subscriber.requests_total = (subscriber.requests_total or 0) + 1
 161 |         subscriber.last_used_at = datetime.utcnow()
 162 | 
 163 |         db.session.commit()
 164 |     except Exception as e:
 165 |         logger.warning("Failed to log API request: %s", e)
 166 |         try:
 167 |             db.session.rollback()
 168 |         except Exception:
 169 |             pass
 170 | 
 171 | 
 172 | def require_api_key(f):
 173 |     """
 174 |     Decorator that validates X-API-Key header on Terminal API endpoints.
 175 |     Injects `_subscriber` kwarg into the decorated function.
 176 |     """
 177 |     @wraps(f)
 178 |     def decorated(*args, **kwargs):
 179 |         from app import db
 180 |         import models
 181 | 
 182 |         start_time = time.monotonic()
 183 |         api_key = request.headers.get("X-API-Key", "").strip()
 184 | 
 185 |         if not api_key:
 186 |             return jsonify({
 187 |                 "error": "Missing X-API-Key header",
 188 |                 "code": "NO_API_KEY",
 189 |                 "docs": "/api/v2/terminal/docs"
 190 |             }), 401
 191 | 
 192 |         try:
 193 |             subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
 194 |         except Exception as e:
 195 |             logger.error("DB error looking up API key: %s", e)
 196 |             return jsonify({"error": "Service temporarily unavailable", "code": "DB_ERROR"}), 503
 197 | 
 198 |         if not subscriber or not subscriber.is_key_valid():
 199 |             return jsonify({
 200 |                 "error": "Invalid or expired API key",
 201 |                 "code": "INVALID_KEY",
 202 |                 "docs": "/api/v2/terminal/docs"
 203 |             }), 401
 204 | 
 205 |         # Rate limit check
 206 |         rate_result = check_rate_limit(subscriber, db, models)
 207 |         if not rate_result["allowed"]:
 208 |             retry_after = rate_result.get("retry_after", 3600)
 209 |             resp = jsonify({
 210 |                 "error": "Rate limit exceeded",
 211 |                 "code": "RATE_LIMITED",
 212 |                 "requests_limit": rate_result["limit"],
 213 |                 "retry_after_seconds": retry_after,
 214 |             })
 215 |             resp.headers["Retry-After"] = str(retry_after)
 216 |             resp.headers["X-RateLimit-Limit"] = str(rate_result["limit"])
 217 |             resp.headers["X-RateLimit-Remaining"] = "0"
 218 |             return resp, 429
 219 | 
 220 |         # Check endpoint entitlement
 221 |         endpoint_path = request.path
 222 |         required_entitlement = ENDPOINT_ENTITLEMENTS.get(endpoint_path)
 223 |         if required_entitlement:
 224 |             ents = subscriber.get_entitlements()
 225 |             if not ents.get(required_entitlement, False):
 226 |                 return jsonify({
 227 |                     "error": f"Your plan does not include '{required_entitlement}' access",
 228 |                     "code": "INSUFFICIENT_TIER",
 229 |                     "upgrade_url": "/premium"
 230 |                 }), 403
 231 | 
 232 |         kwargs["_subscriber"] = subscriber
 233 |         result = f(*args, **kwargs)
 234 | 
 235 |         # Log after response
 236 |         elapsed_ms = int((time.monotonic() - start_time) * 1000)
 237 |         status_code = result[1] if isinstance(result, tuple) else 200
 238 |         log_request(subscriber, endpoint_path, status_code, elapsed_ms, db, models)
 239 | 
 240 |         # Add rate limit headers to response
 241 |         if isinstance(result, tuple):
 242 |             resp, code = result[0], result[1]
 243 |         else:
 244 |             resp, code = result, 200
 245 | 
 246 |         resp.headers["X-RateLimit-Limit"] = str(rate_result["limit"])
 247 |         resp.headers["X-RateLimit-Remaining"] = str(rate_result["remaining"])
 248 |         if subscriber.tier != "enterprise":
 249 |             resp.headers["X-Tier"] = subscriber.tier
 250 | 
 251 |         return resp, code
 252 | 
 253 |     return decorated
 254 | 
 255 | 
 256 | def provision_demo_key(db, models):
 257 |     """
 258 |     Ensure a demo subscriber exists in the DB.
 259 |     Called at app startup. Returns the demo api_key.
 260 |     """
 261 |     DEMO_EMAIL = "demo@protocolpulse.io"
 262 |     DEMO_KEY = "pp_demo_00000000000000000000000000000001"
 263 | 
 264 |     try:
 265 |         existing = models.ApiSubscriber.query.filter_by(email=DEMO_EMAIL).first()
 266 |         if existing:
 267 |             return existing.api_key
 268 | 
 269 |         entitlements = json.dumps(TIER_ENTITLEMENTS.get("demo", {}))
 270 |         demo = models.ApiSubscriber(
 271 |             email=DEMO_EMAIL,
 272 |             api_key=DEMO_KEY,
 273 |             tier="demo",
 274 |             rate_limit_per_hour=20,
 275 |             entitlements=entitlements,
 276 |             key_scopes=json.dumps(["read"]),
 277 |             is_active=True,
 278 |             subscription_status="active",
 279 |         )
 280 |         db.session.add(demo)
 281 |         db.session.commit()
 282 |         logger.info("Demo API key provisioned: %s", DEMO_KEY)
 283 |         return DEMO_KEY
 284 |     except Exception as e:
 285 |         logger.warning("Could not provision demo key: %s", e)
 286 |         try:
 287 |             db.session.rollback()
 288 |         except Exception:
 289 |             pass
 290 |         return DEMO_KEY
 291 | 
 292 | 
 293 | def get_hourly_usage_sparkline(api_key: str, db, models) -> list:
 294 |     """
 295 |     Returns 24 hourly buckets (last 24h) of request counts for the sparkline.
 296 |     Each bucket: {"hour": "HH:00", "count": int}
 297 |     """
 298 |     from models import ApiRequestLog
 299 |     from sqlalchemy import func, extract
 300 | 
 301 |     now = datetime.utcnow()
 302 |     buckets = []
 303 |     try:
 304 |         for i in range(23, -1, -1):
 305 |             bucket_start = now - timedelta(hours=i+1)
 306 |             bucket_end = now - timedelta(hours=i)
 307 |             count = db.session.query(func.count(ApiRequestLog.id)).filter(
 308 |                 ApiRequestLog.api_key == api_key,
 309 |                 ApiRequestLog.created_at >= bucket_start,
 310 |                 ApiRequestLog.created_at < bucket_end,
 311 |             ).scalar() or 0
 312 |             buckets.append({"hour": bucket_start.strftime("%H:00"), "count": count})
 313 |     except Exception as e:
 314 |         logger.warning("sparkline query failed: %s", e)
 315 |     return buckets
 316 | 
```

### File: core/services/stripe_service.py (236 lines)
```
   1 | """
   2 | stripe_service.py — Stripe webhook handler for Pulse Terminal Commander tier.
   3 | Processes subscription events and updates user tier accordingly.
   4 | """
   5 | 
   6 | import logging
   7 | import os
   8 | 
   9 | logger = logging.getLogger("StripeService")
  10 | 
  11 | # Stripe price IDs for Terminal tiers (set in env)
  12 | COMMANDER_PRICE_ID = os.environ.get("STRIPE_COMMANDER_PRICE_ID", "")
  13 | OPERATOR_PRICE_ID = os.environ.get("STRIPE_OPERATOR_PRICE_ID", "")
  14 | SOVEREIGN_PRICE_ID = os.environ.get("STRIPE_SOVEREIGN_PRICE_ID", "")
  15 | 
  16 | _PRICE_TO_TIER = {
  17 |     COMMANDER_PRICE_ID: "commander",
  18 |     OPERATOR_PRICE_ID: "operator",
  19 |     SOVEREIGN_PRICE_ID: "sovereign",
  20 | }
  21 | 
  22 | 
  23 | def resolve_tier_from_price(price_id: str) -> str | None:
  24 |     """Map a Stripe price ID to a subscription tier name. Returns None if unknown."""
  25 |     if not price_id:
  26 |         return None
  27 |     tier = _PRICE_TO_TIER.get(price_id)
  28 |     if tier:
  29 |         return tier
  30 |     # Fallback: check metadata passed in line items
  31 |     return None
  32 | 
  33 | 
  34 | def handle_checkout_completed(session_obj: dict, db, models) -> dict:
  35 |     """
  36 |     Process a checkout.session.completed event for Terminal subscriptions.
  37 |     Upgrades user tier to commander (or whichever tier was purchased).
  38 | 
  39 |     Returns {"success": bool, "tier": str, "user_id": int|None, "error": str|None}
  40 |     """
  41 |     customer_email = (session_obj.get("customer_details") or {}).get("email")
  42 |     customer_id = session_obj.get("customer")
  43 |     subscription_id = session_obj.get("subscription")
  44 | 
  45 |     # Determine tier from metadata first, then price_id fallback
  46 |     metadata = session_obj.get("metadata") or {}
  47 |     tier = metadata.get("tier") or metadata.get("subscription_tier")
  48 | 
  49 |     if not tier:
  50 |         # Try to get from line items metadata if present
  51 |         tier = metadata.get("terminal_tier", "commander")  # default to commander for Terminal
  52 | 
  53 |     if tier not in ("operator", "commander", "sovereign"):
  54 |         logger.warning("Unrecognized tier '%s' in checkout session %s", tier, session_obj.get("id"))
  55 |         return {"success": False, "tier": tier, "user_id": None, "error": "unrecognized tier"}
  56 | 
  57 |     # Find user by email or customer_id
  58 |     user = None
  59 |     if customer_email:
  60 |         user = models.User.query.filter_by(email=customer_email).first()
  61 |     if not user and customer_id:
  62 |         user = models.User.query.filter_by(stripe_customer_id=customer_id).first()
  63 | 
  64 |     if not user:
  65 |         logger.warning("No user found for checkout: email=%s customer=%s", customer_email, customer_id)
  66 |         return {"success": False, "tier": tier, "user_id": None, "error": "user not found"}
  67 | 
  68 |     # Update user tier
  69 |     user.subscription_tier = tier
  70 |     if customer_id:
  71 |         user.stripe_customer_id = customer_id
  72 |     if subscription_id:
  73 |         user.stripe_subscription_id = subscription_id
  74 | 
  75 |     try:
  76 |         db.session.commit()
  77 |         logger.info("User %d upgraded to %s tier via Stripe", user.id, tier)
  78 |         return {"success": True, "tier": tier, "user_id": user.id, "error": None}
  79 |     except Exception as e:
  80 |         db.session.rollback()
  81 |         logger.error("DB error upgrading user %d: %s", user.id, e)
  82 |         return {"success": False, "tier": tier, "user_id": user.id, "error": str(e)}
  83 | 
  84 | 
  85 | def handle_subscription_deleted(subscription_obj: dict, db, models) -> dict:
  86 |     """
  87 |     Process a customer.subscription.deleted event.
  88 |     Downgrades user back to free tier.
  89 |     """
  90 |     subscription_id = subscription_obj.get("id")
  91 |     customer_id = subscription_obj.get("customer")
  92 | 
  93 |     user = None
  94 |     if subscription_id:
  95 |         user = models.User.query.filter_by(stripe_subscription_id=subscription_id).first()
  96 |     if not user and customer_id:
  97 |         user = models.User.query.filter_by(stripe_customer_id=customer_id).first()
  98 | 
  99 |     if not user:
 100 |         logger.warning("No user found for subscription deletion: sub=%s", subscription_id)
 101 |         return {"success": False, "error": "user not found"}
 102 | 
 103 |     old_tier = user.subscription_tier
 104 |     user.subscription_tier = "free"
 105 |     user.stripe_subscription_id = None
 106 | 
 107 |     try:
 108 |         db.session.commit()
 109 |         logger.info("User %d downgraded from %s to free (subscription deleted)", user.id, old_tier)
 110 |         return {"success": True, "user_id": user.id, "old_tier": old_tier}
 111 |     except Exception as e:
 112 |         db.session.rollback()
 113 |         logger.error("DB error downgrading user %d: %s", user.id, e)
 114 |         return {"success": False, "error": str(e)}
 115 | 
 116 | 
 117 | def provision_terminal_subscriber(session_obj: dict, db, models) -> dict:
 118 |     """
 119 |     On checkout.session.completed for Terminal API subscription:
 120 |     Creates/updates ApiSubscriber record with a fresh API key.
 121 |     Returns {"success": bool, "api_key": str|None, "email": str|None, "error": str|None}
 122 |     """
 123 |     import uuid
 124 |     import json
 125 |     from services.api_key_service import generate_api_key, generate_webhook_secret, TIER_ENTITLEMENTS
 126 | 
 127 |     customer_email = (session_obj.get("customer_details") or {}).get("email")
 128 |     if not customer_email:
 129 |         customer_email = session_obj.get("customer_email")
 130 |     customer_id = session_obj.get("customer")
 131 |     subscription_id = session_obj.get("subscription")
 132 |     metadata = session_obj.get("metadata") or {}
 133 | 
 134 |     # Only handle terminal API subscriptions
 135 |     if metadata.get("subscription_type") != "terminal_api":
 136 |         return {"success": False, "api_key": None, "email": customer_email, "error": "not terminal_api"}
 137 | 
 138 |     if not customer_email:
 139 |         logger.warning("No email in terminal checkout session %s", session_obj.get("id"))
 140 |         return {"success": False, "api_key": None, "email": None, "error": "no email"}
 141 | 
 142 |     tier = metadata.get("tier", "commander")
 143 |     if tier not in ("commander", "enterprise"):
 144 |         tier = "commander"
 145 | 
 146 |     try:
 147 |         # Check if subscriber already exists (re-subscription or upgrade)
 148 |         existing = models.ApiSubscriber.query.filter_by(email=customer_email).first()
 149 |         if existing:
 150 |             # Reactivate and update
 151 |             existing.is_active = True
 152 |             existing.subscription_status = "active"
 153 |             existing.tier = tier
 154 |             existing.stripe_customer_id = customer_id
 155 |             existing.stripe_subscription_id = subscription_id
 156 |             existing.entitlements = json.dumps(TIER_ENTITLEMENTS.get(tier, {}))
 157 |             existing.key_scopes = json.dumps(["read", "stream", "webhook"])
 158 |             db.session.commit()
 159 |             logger.info("Terminal subscriber reactivated: %s tier=%s", customer_email, tier)
 160 |             return {"success": True, "api_key": existing.api_key, "email": customer_email, "error": None}
 161 | 
 162 |         # New subscriber
 163 |         new_key = generate_api_key(tier)
 164 |         entitlements = json.dumps(TIER_ENTITLEMENTS.get(tier, {}))
 165 |         subscriber = models.ApiSubscriber(
 166 |             email=customer_email,
 167 |             api_key=new_key,
 168 |             tier=tier,
 169 |             stripe_customer_id=customer_id,
 170 |             stripe_subscription_id=subscription_id,
 171 |             rate_limit_per_hour=1000 if tier == "commander" else -1,
 172 |             entitlements=entitlements,
 173 |             key_scopes=json.dumps(["read", "stream", "webhook"]),
 174 |             is_active=True,
 175 |             subscription_status="active",
 176 |         )
 177 |         db.session.add(subscriber)
 178 |         db.session.commit()
 179 |         logger.info("Terminal subscriber created: %s key=%s... tier=%s",
 180 |                     customer_email, new_key[:20], tier)
 181 |         return {"success": True, "api_key": new_key, "email": customer_email, "error": None}
 182 | 
 183 |     except Exception as e:
 184 |         logger.error("Error provisioning terminal subscriber: %s", e)
 185 |         try:
 186 |             db.session.rollback()
 187 |         except Exception:
 188 |             pass
 189 |         return {"success": False, "api_key": None, "email": customer_email, "error": str(e)}
 190 | 
 191 | 
 192 | def cancel_terminal_subscriber(subscription_obj: dict, db, models) -> dict:
 193 |     """
 194 |     On customer.subscription.deleted: deactivate the ApiSubscriber.
 195 |     """
 196 |     subscription_id = subscription_obj.get("id")
 197 |     customer_id = subscription_obj.get("customer")
 198 | 
 199 |     try:
 200 |         sub = None
 201 |         if subscription_id:
 202 |             sub = models.ApiSubscriber.query.filter_by(stripe_subscription_id=subscription_id).first()
 203 |         if not sub and customer_id:
 204 |             sub = models.ApiSubscriber.query.filter_by(stripe_customer_id=customer_id).first()
 205 | 
 206 |         if not sub:
 207 |             return {"success": False, "error": "subscriber not found"}
 208 | 
 209 |         sub.is_active = False
 210 |         sub.subscription_status = "canceled"
 211 |         db.session.commit()
 212 |         logger.info("Terminal subscriber deactivated: %s", sub.email)
 213 |         return {"success": True, "email": sub.email}
 214 | 
 215 |     except Exception as e:
 216 |         logger.error("Error canceling terminal subscriber: %s", e)
 217 |         try:
 218 |             db.session.rollback()
 219 |         except Exception:
 220 |             pass
 221 |         return {"success": False, "error": str(e)}
 222 | 
 223 | 
 224 | def validate_webhook_signature(payload: bytes, sig_header: str, secret: str) -> dict | None:
 225 |     """
 226 |     Validates Stripe webhook signature. Returns parsed event or None on failure.
 227 |     """
 228 |     try:
 229 |         import stripe
 230 |         stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
 231 |         event = stripe.Webhook.construct_event(payload, sig_header, secret)
 232 |         return event
 233 |     except Exception as e:
 234 |         logger.warning("Stripe signature validation failed: %s", e)
 235 |         return None
 236 | 
```

### File: core/templates/api_dashboard.html (434 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}API Dashboard | Protocol Pulse{% endblock %}
   3 | {% block extra_css %}
   4 | <style>
   5 | .dashboard-page {
   6 |   min-height: 100vh;
   7 |   background: #0a0a0f;
   8 |   padding: 100px 20px 60px;
   9 | }
  10 | .dashboard-container { max-width: 960px; margin: 0 auto; }
  11 | .dash-header { margin-bottom: 36px; }
  12 | .dash-eyebrow {
  13 |   font-family: 'JetBrains Mono', monospace;
  14 |   font-size: 11px; font-weight: 800;
  15 |   letter-spacing: 0.18em; color: #f8c15c;
  16 |   text-transform: uppercase; margin-bottom: 8px;
  17 | }
  18 | .dash-title {
  19 |   font-family: 'JetBrains Mono', monospace;
  20 |   font-size: 26px; font-weight: 700; color: #eef2ff;
  21 | }
  22 | .dash-grid {
  23 |   display: grid;
  24 |   grid-template-columns: repeat(3, 1fr);
  25 |   gap: 16px;
  26 |   margin-bottom: 24px;
  27 | }
  28 | @media (max-width: 768px) { .dash-grid { grid-template-columns: 1fr 1fr; } }
  29 | @media (max-width: 480px) { .dash-grid { grid-template-columns: 1fr; } }
  30 | .stat-card {
  31 |   background: #0d1118;
  32 |   border: 1px solid rgba(255,255,255,0.08);
  33 |   border-radius: 14px;
  34 |   padding: 20px;
  35 | }
  36 | .stat-label {
  37 |   font-family: 'JetBrains Mono', monospace;
  38 |   font-size: 10px; font-weight: 800;
  39 |   letter-spacing: 0.18em; color: #95a0ba;
  40 |   text-transform: uppercase; margin-bottom: 8px;
  41 | }
  42 | .stat-value {
  43 |   font-family: 'JetBrains Mono', monospace;
  44 |   font-size: 28px; font-weight: 900;
  45 |   color: #eef2ff; letter-spacing: -0.02em;
  46 | }
  47 | .stat-value.gold { color: #f8c15c; }
  48 | .stat-sub { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #95a0ba; margin-top: 4px; }
  49 | .panel {
  50 |   background: #0d1118;
  51 |   border: 1px solid rgba(255,255,255,0.08);
  52 |   border-radius: 16px;
  53 |   overflow: hidden;
  54 |   margin-bottom: 20px;
  55 | }
  56 | .panel-header {
  57 |   padding: 16px 20px;
  58 |   border-bottom: 1px solid rgba(255,255,255,0.06);
  59 |   display: flex; align-items: center; justify-content: space-between;
  60 | }
  61 | .panel-title {
  62 |   font-family: 'JetBrains Mono', monospace;
  63 |   font-size: 11px; font-weight: 800;
  64 |   letter-spacing: 0.15em; color: #95a0ba;
  65 |   text-transform: uppercase;
  66 | }
  67 | .panel-body { padding: 20px; }
  68 | .key-row {
  69 |   display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
  70 | }
  71 | .key-masked {
  72 |   flex: 1; min-width: 200px;
  73 |   font-family: 'JetBrains Mono', monospace; font-size: 14px;
  74 |   color: #f8c15c; background: #06070b;
  75 |   border: 1px solid rgba(248,193,92,0.2);
  76 |   border-radius: 8px; padding: 10px 14px;
  77 | }
  78 | .btn-sm {
  79 |   padding: 8px 16px;
  80 |   border-radius: 8px; font-family: 'JetBrains Mono', monospace;
  81 |   font-size: 12px; font-weight: 600; cursor: pointer;
  82 |   border: 1px solid rgba(255,255,255,0.15); background: transparent;
  83 |   color: #eef2ff; transition: all 0.15s;
  84 | }
  85 | .btn-sm:hover { border-color: #f8c15c; color: #f8c15c; }
  86 | .btn-sm.danger { border-color: rgba(255,59,95,0.3); color: #ff8ba0; }
  87 | .btn-sm.danger:hover { border-color: #ff3b5f; background: rgba(255,59,95,0.08); }
  88 | canvas#sparkline { width: 100%; height: 80px; }
  89 | .status-pill {
  90 |   display: inline-flex; align-items: center; gap: 6px;
  91 |   padding: 4px 12px; border-radius: 999px;
  92 |   font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
  93 | }
  94 | .status-pill.active { background: rgba(137,255,184,0.1); color: #89ffb8; border: 1px solid rgba(137,255,184,0.2); }
  95 | .status-pill.canceled { background: rgba(255,59,95,0.1); color: #ff8ba0; border: 1px solid rgba(255,59,95,0.2); }
  96 | .status-pill.past_due { background: rgba(248,193,92,0.1); color: #f8c15c; border: 1px solid rgba(248,193,92,0.2); }
  97 | .entitlement-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
  98 | .ent-chip {
  99 |   padding: 8px 12px; border-radius: 8px; text-align: center;
 100 |   font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
 101 | }
 102 | .ent-chip.on { background: rgba(137,255,184,0.08); color: #89ffb8; border: 1px solid rgba(137,255,184,0.15); }
 103 | .ent-chip.off { background: rgba(255,255,255,0.03); color: #4a5068; border: 1px solid rgba(255,255,255,0.06); }
 104 | .webhook-form { display: flex; gap: 10px; flex-wrap: wrap; }
 105 | .webhook-input {
 106 |   flex: 1; min-width: 200px;
 107 |   background: #06070b; border: 1px solid rgba(255,255,255,0.12);
 108 |   border-radius: 8px; padding: 10px 14px;
 109 |   font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #eef2ff; outline: none;
 110 | }
 111 | .webhook-input:focus { border-color: #f8c15c; }
 112 | .btn-primary {
 113 |   padding: 10px 20px; background: #ff3b5f; border: none;
 114 |   border-radius: 8px; color: #eef2ff; font-family: 'JetBrains Mono', monospace;
 115 |   font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.15s;
 116 | }
 117 | .btn-primary:hover { background: #ff5577; }
 118 | .unauth-card {
 119 |   text-align: center; padding: 60px 40px;
 120 |   background: #0d1118; border: 1px solid rgba(255,255,255,0.08); border-radius: 20px;
 121 | }
 122 | .unauth-title { font-family: 'JetBrains Mono', monospace; font-size: 22px; color: #eef2ff; margin-bottom: 10px; }
 123 | .unauth-sub { color: #95a0ba; margin-bottom: 30px; }
 124 | .key-input-row { display: flex; gap: 10px; max-width: 480px; margin: 0 auto 16px; }
 125 | .key-input {
 126 |   flex: 1; background: #06070b; border: 1px solid rgba(255,255,255,0.12);
 127 |   border-radius: 8px; padding: 12px 16px; font-family: 'JetBrains Mono', monospace;
 128 |   font-size: 13px; color: #eef2ff; outline: none;
 129 | }
 130 | .key-input:focus { border-color: #f8c15c; }
 131 | #rotateModal {
 132 |   display: none; position: fixed; inset: 0;
 133 |   background: rgba(0,0,0,0.8); z-index: 9999;
 134 |   align-items: center; justify-content: center;
 135 | }
 136 | #rotateModal.show { display: flex; }
 137 | .modal-card {
 138 |   background: #0d1118; border: 1px solid rgba(255,59,95,0.3);
 139 |   border-radius: 16px; padding: 36px; max-width: 480px; width: 90%; text-align: center;
 140 | }
 141 | .modal-title { font-family: 'JetBrains Mono', monospace; font-size: 18px; color: #eef2ff; margin-bottom: 12px; }
 142 | .modal-sub { color: #95a0ba; font-size: 14px; margin-bottom: 24px; }
 143 | .modal-actions { display: flex; gap: 12px; justify-content: center; }
 144 | </style>
 145 | {% endblock %}
 146 | {% block content %}
 147 | <div class="dashboard-page">
 148 |   <div class="dashboard-container">
 149 | 
 150 |     {% if subscriber %}
 151 |     <!-- Authenticated dashboard -->
 152 |     <div class="dash-header">
 153 |       <p class="dash-eyebrow">Commander Terminal API</p>
 154 |       <h1 class="dash-title">API Dashboard</h1>
 155 |     </div>
 156 | 
 157 |     <!-- Stat cards -->
 158 |     <div class="dash-grid">
 159 |       <div class="stat-card">
 160 |         <div class="stat-label">Requests Today</div>
 161 |         <div class="stat-value">{{ subscriber.requests_today or 0 }}</div>
 162 |         <div class="stat-sub">of {{ subscriber.rate_limit_per_hour }}/hr limit</div>
 163 |       </div>
 164 |       <div class="stat-card">
 165 |         <div class="stat-label">Total Requests</div>
 166 |         <div class="stat-value gold">{{ "{:,}".format(subscriber.requests_total or 0) }}</div>
 167 |         <div class="stat-sub">lifetime</div>
 168 |       </div>
 169 |       <div class="stat-card">
 170 |         <div class="stat-label">Status</div>
 171 |         <div style="margin-top:8px;">
 172 |           <span class="status-pill {{ subscriber.subscription_status }}">
 173 |             <span style="width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block;"></span>
 174 |             {{ subscriber.subscription_status | upper }}
 175 |           </span>
 176 |         </div>
 177 |         <div class="stat-sub">
 178 |           {% if subscriber.current_period_end %}
 179 |             Renews {{ subscriber.current_period_end.strftime('%b %d, %Y') }}
 180 |           {% else %}Active{% endif %}
 181 |         </div>
 182 |       </div>
 183 |     </div>
 184 | 
 185 |     <!-- API Key panel -->
 186 |     <div class="panel">
 187 |       <div class="panel-header">
 188 |         <span class="panel-title">API Key</span>
 189 |         <span style="font-family:monospace;font-size:11px;color:#95a0ba;">{{ subscriber.tier | upper }}</span>
 190 |       </div>
 191 |       <div class="panel-body">
 192 |         <div class="key-row">
 193 |           <div class="key-masked" id="keyMasked">{{ subscriber.api_key[:12] }}••••••••••••••••••••••••••••••••</div>
 194 |           <button class="btn-sm" onclick="toggleKey()">Reveal</button>
 195 |           <button class="btn-sm" onclick="copyFullKey()">Copy</button>
 196 |           <button class="btn-sm danger" onclick="document.getElementById('rotateModal').classList.add('show')">Rotate Key</button>
 197 |         </div>
 198 |         <p style="font-family:monospace;font-size:11px;color:#95a0ba;margin-top:10px;">
 199 |           Last used: {% if subscriber.last_used_at %}{{ subscriber.last_used_at.strftime('%Y-%m-%d %H:%M UTC') }}{% else %}Never{% endif %}
 200 |         </p>
 201 |       </div>
 202 |     </div>
 203 | 
 204 |     <!-- Sparkline -->
 205 |     <div class="panel">
 206 |       <div class="panel-header">
 207 |         <span class="panel-title">Usage — Last 24h</span>
 208 |       </div>
 209 |       <div class="panel-body">
 210 |         <canvas id="sparkline"></canvas>
 211 |       </div>
 212 |     </div>
 213 | 
 214 |     <!-- Entitlements -->
 215 |     <div class="panel">
 216 |       <div class="panel-header"><span class="panel-title">Entitlements</span></div>
 217 |       <div class="panel-body">
 218 |         <div class="entitlement-grid">
 219 |           {% set ents = subscriber.get_entitlements() %}
 220 |           {% for feat, enabled in ents.items() %}
 221 |           <div class="ent-chip {{ 'on' if enabled else 'off' }}">
 222 |             {{ '✓' if enabled else '✗' }} {{ feat }}
 223 |           </div>
 224 |           {% endfor %}
 225 |         </div>
 226 |       </div>
 227 |     </div>
 228 | 
 229 |     <!-- Webhook config -->
 230 |     {% if subscriber.has_entitlement('webhook') %}
 231 |     <div class="panel">
 232 |       <div class="panel-header"><span class="panel-title">Webhook Delivery</span></div>
 233 |       <div class="panel-body">
 234 |         <p style="color:#95a0ba;font-family:monospace;font-size:12px;margin-bottom:14px;">
 235 |           Receive push notifications when breaking articles are published.
 236 |           Payloads are signed with <code style="color:#f8c15c;">X-PP-Signature: sha256=&lt;hmac&gt;</code>
 237 |         </p>
 238 |         <div class="webhook-form" id="webhookForm">
 239 |           <input type="url" class="webhook-input" id="webhookUrl"
 240 |                  placeholder="https://your-server.com/webhook"
 241 |                  value="{{ subscriber.webhook_url or '' }}">
 242 |           <button class="btn-primary" onclick="saveWebhook()">Save</button>
 243 |         </div>
 244 |         {% if subscriber.webhook_secret %}
 245 |         <p style="font-family:monospace;font-size:11px;color:#95a0ba;margin-top:10px;">
 246 |           Signing secret: <code style="color:#f8c15c;">{{ subscriber.webhook_secret[:16] }}...</code>
 247 |         </p>
 248 |         {% endif %}
 249 |         <div id="webhookMsg" style="display:none;margin-top:10px;font-family:monospace;font-size:12px;"></div>
 250 |       </div>
 251 |     </div>
 252 |     {% endif %}
 253 | 
 254 |     <!-- Billing -->
 255 |     <div class="panel">
 256 |       <div class="panel-header"><span class="panel-title">Billing</span></div>
 257 |       <div class="panel-body" style="display:flex;gap:12px;flex-wrap:wrap;">
 258 |         <button class="btn-primary" onclick="openBillingPortal()">Manage Billing →</button>
 259 |         <a href="/api/playground" class="btn-sm" style="padding:10px 20px;">Playground</a>
 260 |         <a href="/api/v2/terminal/docs" class="btn-sm" style="padding:10px 20px;">API Docs</a>
 261 |       </div>
 262 |     </div>
 263 | 
 264 |     <!-- Rotate Key Modal -->
 265 |     <div id="rotateModal">
 266 |       <div class="modal-card">
 267 |         <h2 class="modal-title">⚠️ Rotate API Key</h2>
 268 |         <p class="modal-sub">Your current key will be immediately invalidated. Update all applications before rotating.</p>
 269 |         <div class="modal-actions">
 270 |           <button class="btn-sm danger" onclick="rotateKey()">Rotate Key</button>
 271 |           <button class="btn-sm" onclick="document.getElementById('rotateModal').classList.remove('show')">Cancel</button>
 272 |         </div>
 273 |         <div id="rotateResult" style="margin-top:16px;font-family:monospace;font-size:12px;display:none;"></div>
 274 |       </div>
 275 |     </div>
 276 | 
 277 |     {% else %}
 278 |     <!-- Unauthenticated -->
 279 |     <div class="unauth-card">
 280 |       <h2 class="unauth-title">API Dashboard</h2>
 281 |       <p class="unauth-sub">Enter your API key to view usage and manage your subscription.</p>
 282 |       <div class="key-input-row">
 283 |         <input type="text" class="key-input" id="keyInput" placeholder="pp_cmd_..." onkeydown="if(event.key==='Enter')lookupKey()">
 284 |         <button class="btn-primary" onclick="lookupKey()">View Dashboard</button>
 285 |       </div>
 286 |       <p style="color:#95a0ba;font-family:monospace;font-size:12px;margin-top:12px;">
 287 |         Don't have a key? <a href="/premium" style="color:#f8c15c;">Get Commander access →</a>
 288 |       </p>
 289 |     </div>
 290 |     {% endif %}
 291 | 
 292 |   </div>
 293 | </div>
 294 | 
 295 | <script>
 296 | {% if subscriber %}
 297 | const FULL_KEY = "{{ api_key }}";
 298 | let keyRevealed = false;
 299 | 
 300 | function toggleKey() {
 301 |   const el = document.getElementById("keyMasked");
 302 |   const btn = event.target;
 303 |   if (!keyRevealed) {
 304 |     el.textContent = FULL_KEY;
 305 |     btn.textContent = "Hide";
 306 |     keyRevealed = true;
 307 |   } else {
 308 |     el.textContent = FULL_KEY.substring(0, 12) + "••••••••••••••••••••••••••••••••";
 309 |     btn.textContent = "Reveal";
 310 |     keyRevealed = false;
 311 |   }
 312 | }
 313 | 
 314 | function copyFullKey() {
 315 |   navigator.clipboard.writeText(FULL_KEY).catch(() => {});
 316 | }
 317 | 
 318 | async function rotateKey() {
 319 |   const resultEl = document.getElementById("rotateResult");
 320 |   resultEl.style.display = "block";
 321 |   resultEl.style.color = "#95a0ba";
 322 |   resultEl.textContent = "Rotating...";
 323 |   try {
 324 |     const resp = await fetch("/api/dashboard/rotate-key", {
 325 |       method: "POST",
 326 |       headers: { "X-API-Key": FULL_KEY }
 327 |     });
 328 |     const data = await resp.json();
 329 |     if (resp.ok) {
 330 |       resultEl.style.color = "#89ffb8";
 331 |       resultEl.textContent = "✓ New key: " + data.new_api_key + "\n\nReload this page and use your new key.";
 332 |     } else {
 333 |       resultEl.style.color = "#ff8ba0";
 334 |       resultEl.textContent = "Error: " + (data.error || "Unknown error");
 335 |     }
 336 |   } catch(e) {
 337 |     resultEl.style.color = "#ff8ba0";
 338 |     resultEl.textContent = "Request failed: " + e.message;
 339 |   }
 340 | }
 341 | 
 342 | async function openBillingPortal() {
 343 |   try {
 344 |     const resp = await fetch("/api/dashboard/billing-portal", {
 345 |       method: "POST",
 346 |       headers: { "X-API-Key": FULL_KEY }
 347 |     });
 348 |     const data = await resp.json();
 349 |     if (data.portal_url) {
 350 |       window.location.href = data.portal_url;
 351 |     } else {
 352 |       alert(data.error || "Billing portal not available. Contact support@protocolpulse.io");
 353 |     }
 354 |   } catch(e) {
 355 |     alert("Could not open billing portal.");
 356 |   }
 357 | }
 358 | 
 359 | async function saveWebhook() {
 360 |   const url = document.getElementById("webhookUrl").value.trim();
 361 |   const msg = document.getElementById("webhookMsg");
 362 |   msg.style.display = "block";
 363 |   msg.style.color = "#95a0ba";
 364 |   msg.textContent = "Saving...";
 365 |   try {
 366 |     const resp = await fetch("/api/dashboard/webhook", {
 367 |       method: "POST",
 368 |       headers: { "X-API-Key": FULL_KEY, "Content-Type": "application/json" },
 369 |       body: JSON.stringify({ webhook_url: url })
 370 |     });
 371 |     const data = await resp.json();
 372 |     if (resp.ok) {
 373 |       msg.style.color = "#89ffb8";
 374 |       msg.textContent = "✓ Webhook saved.";
 375 |     } else {
 376 |       msg.style.color = "#ff8ba0";
 377 |       msg.textContent = "Error: " + (data.error || "Unknown error");
 378 |     }
 379 |   } catch(e) {
 380 |     msg.style.color = "#ff8ba0";
 381 |     msg.textContent = "Request failed.";
 382 |   }
 383 | }
 384 | 
 385 | // Sparkline canvas
 386 | (function() {
 387 |   const raw = {{ sparkline_json|safe }};
 388 |   if (!raw || !raw.length) return;
 389 |   const canvas = document.getElementById("sparkline");
 390 |   if (!canvas) return;
 391 |   const ctx = canvas.getContext("2d");
 392 |   const W = canvas.offsetWidth || 860;
 393 |   const H = 80;
 394 |   canvas.width = W;
 395 |   canvas.height = H;
 396 |   const counts = raw.map(b => b.count);
 397 |   const max = Math.max(...counts, 1);
 398 |   const pad = 8;
 399 |   const stepX = (W - pad * 2) / (counts.length - 1);
 400 |   ctx.strokeStyle = "#f8c15c";
 401 |   ctx.lineWidth = 2;
 402 |   ctx.shadowColor = "rgba(248,193,92,0.4)";
 403 |   ctx.shadowBlur = 6;
 404 |   ctx.beginPath();
 405 |   counts.forEach((v, i) => {
 406 |     const x = pad + i * stepX;
 407 |     const y = H - pad - (v / max) * (H - pad * 2);
 408 |     i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
 409 |   });
 410 |   ctx.stroke();
 411 |   // Fill area
 412 |   ctx.shadowBlur = 0;
 413 |   ctx.strokeStyle = "transparent";
 414 |   const lastX = pad + (counts.length - 1) * stepX;
 415 |   const lastY = H - pad - (counts[counts.length-1] / max) * (H - pad * 2);
 416 |   ctx.lineTo(lastX, H - pad);
 417 |   ctx.lineTo(pad, H - pad);
 418 |   ctx.closePath();
 419 |   const grad = ctx.createLinearGradient(0, 0, 0, H);
 420 |   grad.addColorStop(0, "rgba(248,193,92,0.2)");
 421 |   grad.addColorStop(1, "rgba(248,193,92,0)");
 422 |   ctx.fillStyle = grad;
 423 |   ctx.fill();
 424 | })();
 425 | 
 426 | {% endif %}
 427 | 
 428 | function lookupKey() {
 429 |   const key = document.getElementById("keyInput").value.trim();
 430 |   if (key) window.location.href = "/api/dashboard?key=" + encodeURIComponent(key);
 431 | }
 432 | </script>
 433 | {% endblock %}
 434 | 
```

### File: core/templates/api_playground.html (419 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}API Playground | Protocol Pulse{% endblock %}
   3 | {% block extra_css %}
   4 | <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
   5 | <style>
   6 | .playground-page {
   7 |   min-height: 100vh;
   8 |   background: #0a0a0f;
   9 |   padding: 100px 20px 60px;
  10 | }
  11 | .playground-container {
  12 |   max-width: 1100px;
  13 |   margin: 0 auto;
  14 | }
  15 | .pg-header {
  16 |   text-align: center;
  17 |   margin-bottom: 48px;
  18 | }
  19 | .pg-eyebrow {
  20 |   font-family: 'JetBrains Mono', monospace;
  21 |   font-size: 11px;
  22 |   font-weight: 800;
  23 |   letter-spacing: 0.18em;
  24 |   color: #f8c15c;
  25 |   text-transform: uppercase;
  26 |   margin-bottom: 12px;
  27 | }
  28 | .pg-title {
  29 |   font-family: 'JetBrains Mono', monospace;
  30 |   font-size: 2.2rem;
  31 |   font-weight: 700;
  32 |   color: #eef2ff;
  33 |   margin-bottom: 12px;
  34 | }
  35 | .pg-sub { color: #95a0ba; font-size: 16px; max-width: 560px; margin: 0 auto; }
  36 | .playground-grid {
  37 |   display: grid;
  38 |   grid-template-columns: 380px 1fr;
  39 |   gap: 24px;
  40 |   align-items: start;
  41 | }
  42 | @media (max-width: 768px) {
  43 |   .playground-grid { grid-template-columns: 1fr; }
  44 |   .pg-title { font-size: 1.6rem; }
  45 | }
  46 | .panel {
  47 |   background: #0d1118;
  48 |   border: 1px solid rgba(255,255,255,0.08);
  49 |   border-radius: 16px;
  50 |   overflow: hidden;
  51 | }
  52 | .panel-header {
  53 |   padding: 16px 20px;
  54 |   border-bottom: 1px solid rgba(255,255,255,0.06);
  55 |   display: flex;
  56 |   align-items: center;
  57 |   justify-content: space-between;
  58 | }
  59 | .panel-title {
  60 |   font-family: 'JetBrains Mono', monospace;
  61 |   font-size: 11px;
  62 |   font-weight: 800;
  63 |   letter-spacing: 0.15em;
  64 |   color: #95a0ba;
  65 |   text-transform: uppercase;
  66 | }
  67 | .panel-body { padding: 20px; }
  68 | .form-group { margin-bottom: 18px; }
  69 | .form-label {
  70 |   font-family: 'JetBrains Mono', monospace;
  71 |   font-size: 11px;
  72 |   font-weight: 800;
  73 |   letter-spacing: 0.12em;
  74 |   color: #95a0ba;
  75 |   text-transform: uppercase;
  76 |   display: block;
  77 |   margin-bottom: 8px;
  78 | }
  79 | .form-select, .form-input {
  80 |   width: 100%;
  81 |   background: #06070b;
  82 |   border: 1px solid rgba(255,255,255,0.12);
  83 |   border-radius: 8px;
  84 |   padding: 10px 14px;
  85 |   font-family: 'JetBrains Mono', monospace;
  86 |   font-size: 13px;
  87 |   color: #eef2ff;
  88 |   outline: none;
  89 |   transition: border-color 0.2s;
  90 | }
  91 | .form-select:focus, .form-input:focus { border-color: #f8c15c; }
  92 | .form-select option { background: #0d1118; }
  93 | .key-display {
  94 |   background: #06070b;
  95 |   border: 1px solid rgba(248,193,92,0.2);
  96 |   border-radius: 8px;
  97 |   padding: 10px 14px;
  98 |   font-family: 'JetBrains Mono', monospace;
  99 |   font-size: 12px;
 100 |   color: #f8c15c;
 101 |   word-break: break-all;
 102 |   margin-bottom: 4px;
 103 | }
 104 | .key-note { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #95a0ba; }
 105 | .run-btn {
 106 |   width: 100%;
 107 |   padding: 14px;
 108 |   background: #ff3b5f;
 109 |   border: none;
 110 |   border-radius: 10px;
 111 |   color: #eef2ff;
 112 |   font-family: 'JetBrains Mono', monospace;
 113 |   font-size: 14px;
 114 |   font-weight: 700;
 115 |   cursor: pointer;
 116 |   letter-spacing: 0.08em;
 117 |   transition: all 0.2s;
 118 |   position: relative;
 119 |   overflow: hidden;
 120 | }
 121 | .run-btn:hover { background: #ff5577; transform: translateY(-1px); }
 122 | .run-btn:active { transform: translateY(0); }
 123 | .run-btn.loading { opacity: 0.7; cursor: not-allowed; }
 124 | .lang-tabs {
 125 |   display: flex;
 126 |   gap: 6px;
 127 |   margin-bottom: 14px;
 128 |   flex-wrap: wrap;
 129 | }
 130 | .lang-tab {
 131 |   padding: 6px 14px;
 132 |   border-radius: 6px;
 133 |   font-family: 'JetBrains Mono', monospace;
 134 |   font-size: 11px;
 135 |   font-weight: 700;
 136 |   cursor: pointer;
 137 |   border: 1px solid rgba(255,255,255,0.1);
 138 |   background: transparent;
 139 |   color: #95a0ba;
 140 |   transition: all 0.15s;
 141 | }
 142 | .lang-tab.active {
 143 |   background: rgba(248,193,92,0.12);
 144 |   border-color: rgba(248,193,92,0.3);
 145 |   color: #f8c15c;
 146 | }
 147 | .code-snippet {
 148 |   background: #06070b;
 149 |   border: 1px solid rgba(255,255,255,0.07);
 150 |   border-radius: 10px;
 151 |   padding: 16px;
 152 |   font-family: 'JetBrains Mono', monospace;
 153 |   font-size: 12px;
 154 |   overflow-x: auto;
 155 |   white-space: pre;
 156 |   margin-bottom: 18px;
 157 |   color: #5de4ff;
 158 | }
 159 | .response-area {
 160 |   min-height: 300px;
 161 |   position: relative;
 162 | }
 163 | .response-header {
 164 |   display: flex;
 165 |   align-items: center;
 166 |   justify-content: space-between;
 167 |   margin-bottom: 12px;
 168 | }
 169 | .response-meta {
 170 |   display: flex;
 171 |   gap: 16px;
 172 |   align-items: center;
 173 | }
 174 | .status-badge {
 175 |   font-family: 'JetBrains Mono', monospace;
 176 |   font-size: 12px;
 177 |   font-weight: 700;
 178 |   padding: 4px 10px;
 179 |   border-radius: 6px;
 180 |   display: none;
 181 | }
 182 | .status-badge.ok { background: rgba(137,255,184,0.1); color: #89ffb8; display: inline; }
 183 | .status-badge.err { background: rgba(255,59,95,0.1); color: #ff8ba0; display: inline; }
 184 | .response-time {
 185 |   font-family: 'JetBrains Mono', monospace;
 186 |   font-size: 11px;
 187 |   color: #95a0ba;
 188 |   display: none;
 189 | }
 190 | #responseOutput {
 191 |   background: #06070b;
 192 |   border: 1px solid rgba(255,255,255,0.07);
 193 |   border-radius: 10px;
 194 |   padding: 16px;
 195 |   font-family: 'JetBrains Mono', monospace;
 196 |   font-size: 12px;
 197 |   line-height: 1.7;
 198 |   min-height: 240px;
 199 |   overflow-x: auto;
 200 |   color: #95a0ba;
 201 | }
 202 | .skeleton-line {
 203 |   height: 14px;
 204 |   background: linear-gradient(90deg, #1a1a2e 25%, #252540 50%, #1a1a2e 75%);
 205 |   background-size: 200% 100%;
 206 |   border-radius: 4px;
 207 |   margin-bottom: 10px;
 208 |   animation: shimmer 1.5s infinite;
 209 | }
 210 | @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
 211 | .cta-section {
 212 |   margin-top: 40px;
 213 |   text-align: center;
 214 |   padding: 40px;
 215 |   background: #0d1118;
 216 |   border: 1px solid rgba(248,193,92,0.15);
 217 |   border-radius: 16px;
 218 | }
 219 | .cta-title { font-family: 'JetBrains Mono', monospace; font-size: 22px; color: #eef2ff; margin-bottom: 10px; }
 220 | .cta-sub { color: #95a0ba; margin-bottom: 24px; }
 221 | .cta-btn {
 222 |   display: inline-block;
 223 |   padding: 16px 36px;
 224 |   background: #ff3b5f;
 225 |   border-radius: 10px;
 226 |   color: #eef2ff;
 227 |   font-family: 'JetBrains Mono', monospace;
 228 |   font-size: 15px;
 229 |   font-weight: 700;
 230 |   text-decoration: none;
 231 |   transition: all 0.2s;
 232 |   animation: pulse-border 2s infinite;
 233 | }
 234 | .cta-btn:hover { background: #ff5577; color: #eef2ff; text-decoration: none; transform: translateY(-2px); }
 235 | @keyframes pulse-border {
 236 |   0%,100% { box-shadow: 0 0 0 0 rgba(255,59,95,0.4); }
 237 |   50% { box-shadow: 0 0 0 8px rgba(255,59,95,0); }
 238 | }
 239 | </style>
 240 | {% endblock %}
 241 | {% block content %}
 242 | <div class="playground-page">
 243 |   <div class="playground-container">
 244 |     <div class="pg-header">
 245 |       <p class="pg-eyebrow">Terminal API • Live Demo</p>
 246 |       <h1 class="pg-title">API Playground</h1>
 247 |       <p class="pg-sub">Try every endpoint with a live demo key. Instant results. No signup required.</p>
 248 |     </div>
 249 | 
 250 |     <div class="playground-grid">
 251 |       <!-- Left: Controls -->
 252 |       <div>
 253 |         <div class="panel" style="margin-bottom:20px;">
 254 |           <div class="panel-header">
 255 |             <span class="panel-title">Request Builder</span>
 256 |             <span style="font-family:monospace;font-size:11px;color:#5de4ff;">GET</span>
 257 |           </div>
 258 |           <div class="panel-body">
 259 |             <div class="form-group">
 260 |               <label class="form-label" for="endpointSelect">Endpoint</label>
 261 |               <select class="form-select" id="endpointSelect" onchange="updateSnippet()">
 262 |                 <option value="topics">/api/v2/terminal/topics</option>
 263 |                 <option value="sentiment">/api/v2/terminal/sentiment</option>
 264 |                 <option value="breaking">/api/v2/terminal/breaking</option>
 265 |                 <option value="signal">/api/v2/terminal/signal</option>
 266 |                 <option value="status">/api/v2/terminal/status</option>
 267 |               </select>
 268 |             </div>
 269 |             <div class="form-group">
 270 |               <label class="form-label">API Key</label>
 271 |               <div class="key-display" id="keyDisplay">{{ demo_key }}</div>
 272 |               <p class="key-note">Demo key · 20 req/hr · read-only</p>
 273 |             </div>
 274 |             <button class="run-btn" id="runBtn" onclick="runRequest()">
 275 |               ▶ RUN REQUEST
 276 |             </button>
 277 |           </div>
 278 |         </div>
 279 | 
 280 |         <div class="panel">
 281 |           <div class="panel-header"><span class="panel-title">Code Snippet</span></div>
 282 |           <div class="panel-body">
 283 |             <div class="lang-tabs">
 284 |               <button class="lang-tab active" onclick="setLang('curl', this)">curl</button>
 285 |               <button class="lang-tab" onclick="setLang('python', this)">Python</button>
 286 |               <button class="lang-tab" onclick="setLang('node', this)">Node.js</button>
 287 |             </div>
 288 |             <div id="codeSnippet" class="code-snippet"></div>
 289 |           </div>
 290 |         </div>
 291 |       </div>
 292 | 
 293 |       <!-- Right: Response -->
 294 |       <div class="panel">
 295 |         <div class="panel-header">
 296 |           <span class="panel-title">Response</span>
 297 |           <div class="response-meta">
 298 |             <span class="response-time" id="responseTime"></span>
 299 |             <span class="status-badge" id="statusBadge"></span>
 300 |           </div>
 301 |         </div>
 302 |         <div class="panel-body response-area">
 303 |           <div id="skeletonLoader" style="display:none;">
 304 |             <div class="skeleton-line" style="width:40%"></div>
 305 |             <div class="skeleton-line" style="width:70%"></div>
 306 |             <div class="skeleton-line" style="width:55%"></div>
 307 |             <div class="skeleton-line" style="width:80%"></div>
 308 |             <div class="skeleton-line" style="width:45%"></div>
 309 |           </div>
 310 |           <pre id="responseOutput">// Click RUN REQUEST to see live data
 311 | // Using demo key — 20 requests/hour
 312 | // Upgrade for 1,000 req/hr + full access</pre>
 313 |         </div>
 314 |       </div>
 315 |     </div>
 316 | 
 317 |     <!-- CTA -->
 318 |     <div class="cta-section">
 319 |       <h2 class="cta-title">Ready for Full Access?</h2>
 320 |       <p class="cta-sub">Commander tier — 1,000 requests/hour, SSE stream, webhook delivery, entity tracking</p>
 321 |       <a href="/premium" class="cta-btn">JOIN THE INTEL FEED →</a>
 322 |     </div>
 323 |   </div>
 324 | </div>
 325 | 
 326 | <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
 327 | <script>
 328 | const DEMO_KEY = "{{ demo_key }}";
 329 | const BASE_URL = window.location.origin;
 330 | const ENDPOINTS = {
 331 |   topics:    "/api/v2/terminal/topics",
 332 |   sentiment: "/api/v2/terminal/sentiment",
 333 |   breaking:  "/api/v2/terminal/breaking",
 334 |   signal:    "/api/v2/terminal/signal",
 335 |   status:    "/api/v2/terminal/status",
 336 | };
 337 | 
 338 | let currentLang = "curl";
 339 | 
 340 | const SNIPPETS = {
 341 |   curl: (ep) => `curl ${BASE_URL}${ENDPOINTS[ep]} \\\n  -H "X-API-Key: ${DEMO_KEY}"`,
 342 |   python: (ep) => `import requests\n\nresponse = requests.get(\n    "${BASE_URL}${ENDPOINTS[ep]}",\n    headers={"X-API-Key": "${DEMO_KEY}"}\n)\nprint(response.json())`,
 343 |   node: (ep) => `const resp = await fetch("${BASE_URL}${ENDPOINTS[ep]}", {\n  headers: { "X-API-Key": "${DEMO_KEY}" }\n});\nconst data = await resp.json();\nconsole.log(data);`,
 344 | };
 345 | 
 346 | function getEndpoint() {
 347 |   return document.getElementById("endpointSelect").value;
 348 | }
 349 | 
 350 | function updateSnippet() {
 351 |   const ep = getEndpoint();
 352 |   const el = document.getElementById("codeSnippet");
 353 |   el.textContent = SNIPPETS[currentLang](ep);
 354 |   if (window.Prism) Prism.highlightElement(el);
 355 | }
 356 | 
 357 | function setLang(lang, btn) {
 358 |   currentLang = lang;
 359 |   document.querySelectorAll(".lang-tab").forEach(t => t.classList.remove("active"));
 360 |   btn.classList.add("active");
 361 |   updateSnippet();
 362 | }
 363 | 
 364 | function showSkeleton(show) {
 365 |   document.getElementById("skeletonLoader").style.display = show ? "block" : "none";
 366 |   document.getElementById("responseOutput").style.display = show ? "none" : "block";
 367 | }
 368 | 
 369 | async function runRequest() {
 370 |   const ep = getEndpoint();
 371 |   const url = BASE_URL + ENDPOINTS[ep];
 372 |   const btn = document.getElementById("runBtn");
 373 |   const statusBadge = document.getElementById("statusBadge");
 374 |   const timeBadge = document.getElementById("responseTime");
 375 |   const output = document.getElementById("responseOutput");
 376 | 
 377 |   btn.classList.add("loading");
 378 |   btn.textContent = "Running...";
 379 |   showSkeleton(true);
 380 |   statusBadge.style.display = "none";
 381 |   timeBadge.style.display = "none";
 382 | 
 383 |   const start = performance.now();
 384 |   try {
 385 |     const resp = await fetch(url, {
 386 |       headers: { "X-API-Key": DEMO_KEY }
 387 |     });
 388 |     const elapsed = Math.round(performance.now() - start);
 389 |     const data = await resp.json();
 390 | 
 391 |     showSkeleton(false);
 392 |     output.textContent = JSON.stringify(data, null, 2);
 393 |     if (window.Prism) {
 394 |       output.className = "language-json";
 395 |       Prism.highlightElement(output);
 396 |     }
 397 | 
 398 |     statusBadge.textContent = resp.status + " " + (resp.ok ? "OK" : "ERROR");
 399 |     statusBadge.className = "status-badge " + (resp.ok ? "ok" : "err");
 400 |     statusBadge.style.display = "inline";
 401 |     timeBadge.textContent = elapsed + "ms";
 402 |     timeBadge.style.display = "inline";
 403 |   } catch (err) {
 404 |     showSkeleton(false);
 405 |     output.textContent = "// Error: " + err.message;
 406 |     statusBadge.textContent = "ERROR";
 407 |     statusBadge.className = "status-badge err";
 408 |     statusBadge.style.display = "inline";
 409 |   } finally {
 410 |     btn.classList.remove("loading");
 411 |     btn.textContent = "▶ RUN REQUEST";
 412 |   }
 413 | }
 414 | 
 415 | // Init
 416 | updateSnippet();
 417 | </script>
 418 | {% endblock %}
 419 | 
```

### File: core/templates/premium.html (544 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Upgrade to Premium | Protocol Pulse{% endblock %}
   4 | 
   5 | {% block head %}
   6 | <style>
   7 | :root {
   8 |     --pp-red: #dc2626;
   9 |     --pp-dark: #0a0a0a;
  10 |     --pp-glass: rgba(10, 10, 10, 0.95);
  11 |     --gold: #f59e0b;
  12 |     --btc-orange: #f7931a;
  13 | }
  14 | 
  15 | .premium-page {
  16 |     min-height: 100vh;
  17 |     background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
  18 |     padding: 100px 20px 60px;
  19 | }
  20 | 
  21 | .premium-container {
  22 |     max-width: 1200px;
  23 |     margin: 0 auto;
  24 | }
  25 | 
  26 | .premium-header {
  27 |     text-align: center;
  28 |     margin-bottom: 50px;
  29 | }
  30 | 
  31 | .premium-title {
  32 |     font-family: 'JetBrains Mono', monospace;
  33 |     font-size: 2.5rem;
  34 |     color: #fff;
  35 |     margin-bottom: 15px;
  36 | }
  37 | 
  38 | .premium-title span {
  39 |     background: linear-gradient(135deg, var(--gold), var(--btc-orange));
  40 |     -webkit-background-clip: text;
  41 |     -webkit-text-fill-color: transparent;
  42 |     background-clip: text;
  43 | }
  44 | 
  45 | .premium-subtitle {
  46 |     font-family: 'JetBrains Mono', monospace;
  47 |     font-size: 1rem;
  48 |     color: rgba(255, 255, 255, 0.6);
  49 |     max-width: 600px;
  50 |     margin: 0 auto;
  51 | }
  52 | 
  53 | .pricing-grid {
  54 |     display: grid;
  55 |     grid-template-columns: repeat(4, 1fr);
  56 |     gap: 25px;
  57 |     margin-bottom: 60px;
  58 | }
  59 | 
  60 | @media (max-width: 1200px) {
  61 |     .pricing-grid {
  62 |         grid-template-columns: repeat(2, 1fr);
  63 |     }
  64 | }
  65 | 
  66 | @media (max-width: 992px) {
  67 |     .pricing-grid {
  68 |         grid-template-columns: 1fr;
  69 |         max-width: 400px;
  70 |         margin: 0 auto 60px;
  71 |     }
  72 | }
  73 | 
  74 | .pricing-card {
  75 |     background: var(--pp-glass);
  76 |     border: 1px solid rgba(255, 255, 255, 0.1);
  77 |     border-radius: 20px;
  78 |     padding: 35px;
  79 |     position: relative;
  80 |     transition: all 0.3s ease;
  81 | }
  82 | 
  83 | .pricing-card:hover {
  84 |     transform: translateY(-5px);
  85 | }
  86 | 
  87 | .pricing-card.featured {
  88 |     border-color: var(--gold);
  89 |     box-shadow: 0 0 40px rgba(245, 158, 11, 0.2);
  90 | }
  91 | 
  92 | .pricing-card.featured::before {
  93 |     content: 'MOST POPULAR';
  94 |     position: absolute;
  95 |     top: -12px;
  96 |     left: 50%;
  97 |     transform: translateX(-50%);
  98 |     background: var(--gold);
  99 |     color: #000;
 100 |     padding: 6px 20px;
 101 |     border-radius: 20px;
 102 |     font-family: 'JetBrains Mono', monospace;
 103 |     font-size: 0.7rem;
 104 |     font-weight: 700;
 105 |     letter-spacing: 1px;
 106 | }
 107 | 
 108 | .tier-name {
 109 |     font-family: 'JetBrains Mono', monospace;
 110 |     font-size: 0.9rem;
 111 |     color: rgba(255, 255, 255, 0.5);
 112 |     text-transform: uppercase;
 113 |     letter-spacing: 2px;
 114 |     margin-bottom: 10px;
 115 | }
 116 | 
 117 | .tier-title {
 118 |     font-family: 'JetBrains Mono', monospace;
 119 |     font-size: 1.5rem;
 120 |     color: #fff;
 121 |     font-weight: 600;
 122 |     margin-bottom: 20px;
 123 | }
 124 | 
 125 | .tier-price {
 126 |     margin-bottom: 25px;
 127 | }
 128 | 
 129 | .price-amount {
 130 |     font-family: 'JetBrains Mono', monospace;
 131 |     font-size: 3rem;
 132 |     font-weight: 700;
 133 |     color: #fff;
 134 | }
 135 | 
 136 | .featured .price-amount {
 137 |     color: var(--gold);
 138 | }
 139 | 
 140 | .price-period {
 141 |     font-family: 'JetBrains Mono', monospace;
 142 |     font-size: 0.9rem;
 143 |     color: rgba(255, 255, 255, 0.5);
 144 | }
 145 | 
 146 | .sats-price {
 147 |     font-family: 'JetBrains Mono', monospace;
 148 |     font-size: 0.8rem;
 149 |     color: var(--btc-orange);
 150 |     margin-top: 5px;
 151 | }
 152 | 
 153 | .features-list {
 154 |     list-style: none;
 155 |     padding: 0;
 156 |     margin: 0 0 30px;
 157 | }
 158 | 
 159 | .features-list li {
 160 |     display: flex;
 161 |     align-items: flex-start;
 162 |     gap: 12px;
 163 |     padding: 10px 0;
 164 |     font-family: 'JetBrains Mono', monospace;
 165 |     font-size: 0.85rem;
 166 |     color: rgba(255, 255, 255, 0.8);
 167 | }
 168 | 
 169 | .features-list li i {
 170 |     color: #22c55e;
 171 |     margin-top: 3px;
 172 | }
 173 | 
 174 | .subscribe-btn {
 175 |     width: 100%;
 176 |     padding: 16px;
 177 |     border-radius: 12px;
 178 |     font-family: 'JetBrains Mono', monospace;
 179 |     font-size: 0.95rem;
 180 |     font-weight: 600;
 181 |     cursor: pointer;
 182 |     transition: all 0.3s ease;
 183 |     text-decoration: none;
 184 |     display: block;
 185 |     text-align: center;
 186 | }
 187 | 
 188 | .subscribe-btn.primary {
 189 |     background: var(--gold);
 190 |     border: none;
 191 |     color: #000;
 192 | }
 193 | 
 194 | .subscribe-btn.primary:hover {
 195 |     background: #d97706;
 196 | }
 197 | 
 198 | .subscribe-btn.secondary {
 199 |     background: transparent;
 200 |     border: 1px solid rgba(255, 255, 255, 0.2);
 201 |     color: #fff;
 202 | }
 203 | 
 204 | .subscribe-btn.secondary:hover {
 205 |     border-color: var(--gold);
 206 |     color: var(--gold);
 207 | }
 208 | 
 209 | .subscribe-btn.free {
 210 |     background: rgba(255, 255, 255, 0.05);
 211 |     border: 1px solid rgba(255, 255, 255, 0.1);
 212 |     color: rgba(255, 255, 255, 0.6);
 213 | }
 214 | 
 215 | .faq-section {
 216 |     max-width: 800px;
 217 |     margin: 0 auto;
 218 | }
 219 | 
 220 | .faq-title {
 221 |     font-family: 'JetBrains Mono', monospace;
 222 |     font-size: 1.5rem;
 223 |     color: #fff;
 224 |     text-align: center;
 225 |     margin-bottom: 30px;
 226 | }
 227 | 
 228 | .faq-item {
 229 |     background: var(--pp-glass);
 230 |     border: 1px solid rgba(255, 255, 255, 0.1);
 231 |     border-radius: 12px;
 232 |     margin-bottom: 15px;
 233 |     overflow: hidden;
 234 | }
 235 | 
 236 | .faq-question {
 237 |     padding: 20px;
 238 |     font-family: 'JetBrains Mono', monospace;
 239 |     font-size: 0.95rem;
 240 |     color: #fff;
 241 |     cursor: pointer;
 242 |     display: flex;
 243 |     justify-content: space-between;
 244 |     align-items: center;
 245 | }
 246 | 
 247 | .faq-question:hover {
 248 |     background: rgba(255, 255, 255, 0.03);
 249 | }
 250 | 
 251 | .faq-answer {
 252 |     padding: 0 20px 20px;
 253 |     font-family: 'JetBrains Mono', monospace;
 254 |     font-size: 0.85rem;
 255 |     color: rgba(255, 255, 255, 0.7);
 256 |     line-height: 1.6;
 257 |     display: none;
 258 | }
 259 | 
 260 | .faq-item.active .faq-answer {
 261 |     display: block;
 262 | }
 263 | 
 264 | .payment-methods {
 265 |     text-align: center;
 266 |     margin-top: 40px;
 267 |     padding-top: 40px;
 268 |     border-top: 1px solid rgba(255, 255, 255, 0.1);
 269 | }
 270 | 
 271 | .payment-title {
 272 |     font-family: 'JetBrains Mono', monospace;
 273 |     font-size: 0.8rem;
 274 |     color: rgba(255, 255, 255, 0.5);
 275 |     text-transform: uppercase;
 276 |     letter-spacing: 1px;
 277 |     margin-bottom: 15px;
 278 | }
 279 | 
 280 | .payment-icons {
 281 |     display: flex;
 282 |     justify-content: center;
 283 |     gap: 20px;
 284 |     flex-wrap: wrap;
 285 | }
 286 | 
 287 | .payment-icon {
 288 |     width: 50px;
 289 |     height: 30px;
 290 |     background: rgba(255, 255, 255, 0.1);
 291 |     border-radius: 6px;
 292 |     display: flex;
 293 |     align-items: center;
 294 |     justify-content: center;
 295 |     color: rgba(255, 255, 255, 0.6);
 296 |     font-size: 1.2rem;
 297 | }
 298 | 
 299 | .payment-icon.btc {
 300 |     color: var(--btc-orange);
 301 | }
 302 | </style>
 303 | {% endblock %}
 304 | 
 305 | {% block content %}
 306 | <div class="premium-page">
 307 |     <div class="premium-container">
 308 |         {% if current_user.is_authenticated and current_user.has_commander_tier() %}
 309 |         <div class="text-center mb-4 p-3" style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 12px;">
 310 |             <a href="{{ url_for('premium_hub') }}" class="subscribe-btn primary" style="display: inline-block; width: auto; padding: 12px 24px;">
 311 |                 <i class="fas fa-bolt me-2"></i>Go to Premium Hub
 312 |             </a>
 313 |         </div>
 314 |         {% endif %}
 315 |         <div class="premium-header">
 316 |             <h1 class="premium-title">Upgrade to <span>Premium Intelligence</span></h1>
 317 |             <p class="premium-subtitle">Access exclusive research, strategy calls, and priority intel alerts. Pay with card or Bitcoin.</p>
 318 |         </div>
 319 | 
 320 |         <!-- Terminal API Section -->
 321 |         <div style="margin-bottom:60px;padding:40px;background:linear-gradient(135deg,rgba(13,17,24,0.95),rgba(6,7,11,0.98));border:1px solid rgba(248,193,92,0.25);border-radius:20px;box-shadow:0 0 60px rgba(248,193,92,0.06);">
 322 |             <div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:center;" class="terminal-api-grid">
 323 |                 <div>
 324 |                     <p style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:800;letter-spacing:0.2em;color:#f8c15c;text-transform:uppercase;margin-bottom:10px;">TERMINAL API &bull; DEVELOPER ACCESS</p>
 325 |                     <h2 style="font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;color:#eef2ff;margin-bottom:12px;line-height:1.2;">Bitcoin Intelligence<br>as a Data Feed</h2>
 326 |                     <p style="color:#95a0ba;font-size:15px;line-height:1.6;margin-bottom:24px;">Real-time topics, sentiment, entities, breaking news — all via REST API. Build apps, bots, and dashboards on Protocol Pulse data.</p>
 327 |                     <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:28px;">
 328 |                         <div style="display:flex;align-items:center;gap:10px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#eef2ff;"><span style="color:#f8c15c;">⚡</span> 1,000 requests/hour</div>
 329 |                         <div style="display:flex;align-items:center;gap:10px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#eef2ff;"><span style="color:#f8c15c;">📡</span> SSE real-time breaking news stream</div>
 330 |                         <div style="display:flex;align-items:center;gap:10px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#eef2ff;"><span style="color:#f8c15c;">🔗</span> Webhook push delivery</div>
 331 |                         <div style="display:flex;align-items:center;gap:10px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#eef2ff;"><span style="color:#f8c15c;">📊</span> Topics, entities, sentiment, signal strength</div>
 332 |                     </div>
 333 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:36px;font-weight:700;color:#f8c15c;line-height:1;margin-bottom:4px;">$49<span style="font-size:16px;color:#95a0ba;">/mo</span></div>
 334 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#95a0ba;">Commander Tier &bull; Cancel anytime</div>
 335 |                 </div>
 336 |                 <div>
 337 |                     <div style="background:#06070b;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:20px;font-family:'JetBrains Mono',monospace;margin-bottom:16px;">
 338 |                         <div style="color:#95a0ba;font-size:10px;letter-spacing:0.15em;margin-bottom:10px;">SAMPLE RESPONSE</div>
 339 |                         <pre style="color:#5de4ff;margin:0;overflow-x:auto;font-size:11px;line-height:1.6;">{
 340 |   "data": [
 341 |     {"topic": "halving", "mentions": 42},
 342 |     {"topic": "etf", "mentions": 31},
 343 |     {"topic": "lightning", "mentions": 18}
 344 |   ],
 345 |   "meta": {
 346 |     "tier": "commander",
 347 |     "requests_remaining": 987
 348 |   }
 349 | }</pre>
 350 |                     </div>
 351 |                     <div style="display:flex;gap:10px;margin-bottom:10px;" id="terminalApiForm">
 352 |                         <input type="email" id="terminalEmail" placeholder="your@email.com"
 353 |                             style="flex:1;background:#06070b;border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:12px 14px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#eef2ff;outline:none;"
 354 |                             onfocus="this.style.borderColor='#f8c15c'" onblur="this.style.borderColor='rgba(255,255,255,0.15)'">
 355 |                         <button onclick="startTerminalCheckout()" id="terminalBtn"
 356 |                             style="padding:12px 18px;background:#ff3b5f;border:none;border-radius:8px;color:#eef2ff;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;transition:background 0.2s;"
 357 |                             onmouseover="this.style.background='#ff5577'" onmouseout="this.style.background='#ff3b5f'">
 358 |                             JOIN THE INTEL FEED &rarr;
 359 |                         </button>
 360 |                     </div>
 361 |                     <div id="terminalCheckoutMsg" style="display:none;margin-bottom:10px;font-family:'JetBrains Mono',monospace;font-size:12px;"></div>
 362 |                     <div style="display:flex;gap:16px;">
 363 |                         <a href="/api/playground" style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#f8c15c;text-decoration:none;">Try Playground &rarr;</a>
 364 |                         <a href="/api/v2/terminal/docs" style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#95a0ba;text-decoration:none;">API Docs &rarr;</a>
 365 |                         <a href="/api/dashboard" style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#95a0ba;text-decoration:none;">Dashboard &rarr;</a>
 366 |                     </div>
 367 |                 </div>
 368 |             </div>
 369 |         </div>
 370 |         <style>
 371 |         .terminal-api-grid { }
 372 |         @media(max-width:768px){ .terminal-api-grid { grid-template-columns: 1fr !important; } }
 373 |         </style>
 374 |         
 375 |         <div class="pricing-grid">
 376 |             <div class="pricing-card">
 377 |                 <div class="tier-name">Starter</div>
 378 |                 <div class="tier-title">{{ tiers.free.name }}</div>
 379 |                 <div class="tier-price">
 380 |                     <span class="price-amount">$0</span>
 381 |                     <span class="price-period">/forever</span>
 382 |                 </div>
 383 |                 <ul class="features-list">
 384 |                     {% for feature in tiers.free.features %}
 385 |                     <li><i class="fas fa-check"></i> {{ feature }}</li>
 386 |                     {% endfor %}
 387 |                 </ul>
 388 |                 <a href="/register" class="subscribe-btn free">Current Plan</a>
 389 |             </div>
 390 |             
 391 |             <div class="pricing-card">
 392 |                 <div class="tier-name">Starter</div>
 393 |                 <div class="tier-title">{{ tiers.operator.name }}</div>
 394 |                 <div class="tier-price">
 395 |                     <span class="price-amount">${{ tiers.operator.price_monthly }}</span>
 396 |                     <span class="price-period">/month</span>
 397 |                 </div>
 398 |                 <ul class="features-list">
 399 |                     {% for feature in tiers.operator.features[:4] %}
 400 |                     <li><i class="fas fa-check"></i> {{ feature }}</li>
 401 |                     {% endfor %}
 402 |                 </ul>
 403 |                 <a href="/subscribe/premium/operator" class="subscribe-btn secondary">Upgrade</a>
 404 |             </div>
 405 |             
 406 |             <div class="pricing-card featured">
 407 |                 <div class="tier-name">Best value</div>
 408 |                 <div class="tier-title">{{ tiers.commander.name }}</div>
 409 |                 <div class="tier-price">
 410 |                     <span class="price-amount">${{ tiers.commander.price_monthly }}</span>
 411 |                     <span class="price-period">/month</span>
 412 |                     <div class="sats-price">Premium Hub · Real-time intel</div>
 413 |                 </div>
 414 |                 <ul class="features-list">
 415 |                     {% for feature in tiers.commander.features[:5] %}
 416 |                     <li><i class="fas fa-check"></i> {{ feature }}</li>
 417 |                     {% endfor %}
 418 |                 </ul>
 419 |                 <a href="/subscribe/premium/commander" class="subscribe-btn primary">Get Premium Hub</a>
 420 |             </div>
 421 |             
 422 |             <div class="pricing-card">
 423 |                 <div class="tier-name">Elite</div>
 424 |                 <div class="tier-title">{{ tiers.sovereign.name }}</div>
 425 |                 <div class="tier-price">
 426 |                     <span class="price-amount">${{ tiers.sovereign.price_monthly }}</span>
 427 |                     <span class="price-period">/month</span>
 428 |                     <div class="sats-price">~210,000 sats/month</div>
 429 |                 </div>
 430 |                 <ul class="features-list">
 431 |                     {% for feature in tiers.sovereign.features %}
 432 |                     <li><i class="fas fa-check"></i> {{ feature }}</li>
 433 |                     {% endfor %}
 434 |                 </ul>
 435 |                 <a href="/subscribe/premium/sovereign" class="subscribe-btn secondary">Go Sovereign</a>
 436 |             </div>
 437 |         </div>
 438 |         
 439 |         <div class="faq-section">
 440 |             <h2 class="faq-title">Frequently Asked Questions</h2>
 441 |             
 442 |             <div class="faq-item">
 443 |                 <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
 444 |                     Can I pay with Bitcoin?
 445 |                     <i class="fas fa-chevron-down"></i>
 446 |                 </div>
 447 |                 <div class="faq-answer">
 448 |                     Yes! We accept both on-chain Bitcoin and Lightning payments. After checkout, you'll receive an invoice you can pay with any Bitcoin wallet. Lightning payments are instant.
 449 |                 </div>
 450 |             </div>
 451 |             
 452 |             <div class="faq-item">
 453 |                 <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
 454 |                     What's the refund policy?
 455 |                     <i class="fas fa-chevron-down"></i>
 456 |                 </div>
 457 |                 <div class="faq-answer">
 458 |                     We offer a 7-day money-back guarantee. If you're not satisfied within the first week, contact us for a full refund. After 7 days, you can cancel anytime but no refunds are provided for the current billing period.
 459 |                 </div>
 460 |             </div>
 461 |             
 462 |             <div class="faq-item">
 463 |                 <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
 464 |                     How do I access premium content?
 465 |                     <i class="fas fa-chevron-down"></i>
 466 |                 </div>
 467 |                 <div class="faq-answer">
 468 |                     After subscribing, you'll get access to the private Discord/Telegram channels, premium articles marked with a gold badge, and strategy call invites via email. Everything is linked to your account.
 469 |                 </div>
 470 |             </div>
 471 |             
 472 |             <div class="faq-item">
 473 |                 <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
 474 |                     Can I upgrade or downgrade later?
 475 |                     <i class="fas fa-chevron-down"></i>
 476 |                 </div>
 477 |                 <div class="faq-answer">
 478 |                     Absolutely. You can change your plan at any time from your account settings. Upgrades take effect immediately, and downgrades apply at the end of your current billing period.
 479 |                 </div>
 480 |             </div>
 481 |         </div>
 482 |         
 483 |         <div class="payment-methods">
 484 |             <div class="payment-title">Accepted Payment Methods</div>
 485 |             <div class="payment-icons">
 486 |                 <div class="payment-icon btc"><i class="fab fa-bitcoin"></i></div>
 487 |                 <div class="payment-icon"><i class="fas fa-bolt"></i></div>
 488 |                 <div class="payment-icon"><i class="fab fa-cc-visa"></i></div>
 489 |                 <div class="payment-icon"><i class="fab fa-cc-mastercard"></i></div>
 490 |                 <div class="payment-icon"><i class="fab fa-apple-pay"></i></div>
 491 |             </div>
 492 |         </div>
 493 |     </div>
 494 | </div>
 495 | {% block extra_js %}
 496 | <script>
 497 | async function startTerminalCheckout() {
 498 |     const emailEl = document.getElementById('terminalEmail');
 499 |     const btn = document.getElementById('terminalBtn');
 500 |     const msg = document.getElementById('terminalCheckoutMsg');
 501 |     const email = (emailEl ? emailEl.value : '').trim();
 502 | 
 503 |     if (!email || !email.includes('@')) {
 504 |         msg.style.display = 'block';
 505 |         msg.style.color = '#ff8ba0';
 506 |         msg.textContent = 'Please enter a valid email address.';
 507 |         return;
 508 |     }
 509 | 
 510 |     btn.disabled = true;
 511 |     btn.textContent = 'Loading...';
 512 |     msg.style.display = 'block';
 513 |     msg.style.color = '#95a0ba';
 514 |     msg.textContent = 'Creating checkout session...';
 515 | 
 516 |     try {
 517 |         const resp = await fetch('/api/v2/terminal/subscribe', {
 518 |             method: 'POST',
 519 |             headers: { 'Content-Type': 'application/json' },
 520 |             body: JSON.stringify({ email })
 521 |         });
 522 |         const data = await resp.json();
 523 | 
 524 |         if (resp.ok && data.checkout_url) {
 525 |             msg.style.color = '#89ffb8';
 526 |             msg.textContent = 'Redirecting to Stripe...';
 527 |             window.location.href = data.checkout_url;
 528 |         } else {
 529 |             msg.style.color = '#ff8ba0';
 530 |             msg.textContent = data.error || 'Checkout unavailable. Contact support@protocolpulse.io';
 531 |             btn.disabled = false;
 532 |             btn.textContent = 'JOIN THE INTEL FEED \u2192';
 533 |         }
 534 |     } catch (e) {
 535 |         msg.style.color = '#ff8ba0';
 536 |         msg.textContent = 'Request failed. Please try again.';
 537 |         btn.disabled = false;
 538 |         btn.textContent = 'JOIN THE INTEL FEED \u2192';
 539 |     }
 540 | }
 541 | </script>
 542 | {% endblock %}
 543 | {% endblock %}
 544 | 
```

### File: core/templates/subscribe_terminal_success.html (267 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}API Key Ready | Protocol Pulse{% endblock %}
   3 | {% block extra_css %}
   4 | <style>
   5 | .success-page {
   6 |   min-height: 100vh;
   7 |   background: linear-gradient(135deg, #0a0a0f 0%, #0d0612 100%);
   8 |   display: flex;
   9 |   align-items: center;
  10 |   justify-content: center;
  11 |   padding: 40px 20px;
  12 | }
  13 | .success-card {
  14 |   background: #0d1118;
  15 |   border: 1px solid rgba(248, 193, 92, 0.3);
  16 |   border-radius: 20px;
  17 |   padding: 48px;
  18 |   max-width: 600px;
  19 |   width: 100%;
  20 |   box-shadow: 0 0 60px rgba(248, 193, 92, 0.08);
  21 | }
  22 | .success-icon {
  23 |   width: 64px;
  24 |   height: 64px;
  25 |   background: rgba(248, 193, 92, 0.1);
  26 |   border: 2px solid rgba(248, 193, 92, 0.4);
  27 |   border-radius: 50%;
  28 |   display: flex;
  29 |   align-items: center;
  30 |   justify-content: center;
  31 |   margin: 0 auto 24px;
  32 |   font-size: 28px;
  33 | }
  34 | .success-eyebrow {
  35 |   text-align: center;
  36 |   font-family: 'JetBrains Mono', monospace;
  37 |   font-size: 11px;
  38 |   font-weight: 800;
  39 |   letter-spacing: 0.18em;
  40 |   color: #f8c15c;
  41 |   text-transform: uppercase;
  42 |   margin-bottom: 12px;
  43 | }
  44 | .success-title {
  45 |   text-align: center;
  46 |   font-family: 'JetBrains Mono', monospace;
  47 |   font-size: 28px;
  48 |   font-weight: 700;
  49 |   color: #eef2ff;
  50 |   margin-bottom: 8px;
  51 | }
  52 | .success-sub {
  53 |   text-align: center;
  54 |   color: #95a0ba;
  55 |   font-size: 15px;
  56 |   margin-bottom: 32px;
  57 | }
  58 | .key-box {
  59 |   background: #06070b;
  60 |   border: 1px solid rgba(248, 193, 92, 0.25);
  61 |   border-radius: 12px;
  62 |   padding: 20px 24px;
  63 |   margin-bottom: 24px;
  64 | }
  65 | .key-label {
  66 |   font-family: 'JetBrains Mono', monospace;
  67 |   font-size: 10px;
  68 |   font-weight: 800;
  69 |   letter-spacing: 0.18em;
  70 |   color: #95a0ba;
  71 |   text-transform: uppercase;
  72 |   margin-bottom: 10px;
  73 | }
  74 | .key-value {
  75 |   font-family: 'JetBrains Mono', monospace;
  76 |   font-size: 14px;
  77 |   color: #f8c15c;
  78 |   word-break: break-all;
  79 |   line-height: 1.6;
  80 | }
  81 | .key-actions {
  82 |   display: flex;
  83 |   gap: 10px;
  84 |   margin-top: 12px;
  85 |   flex-wrap: wrap;
  86 | }
  87 | .btn-copy {
  88 |   background: rgba(248, 193, 92, 0.1);
  89 |   border: 1px solid rgba(248, 193, 92, 0.3);
  90 |   color: #f8c15c;
  91 |   border-radius: 8px;
  92 |   padding: 8px 16px;
  93 |   font-family: 'JetBrains Mono', monospace;
  94 |   font-size: 12px;
  95 |   font-weight: 600;
  96 |   cursor: pointer;
  97 |   transition: all 0.2s;
  98 | }
  99 | .btn-copy:hover { background: rgba(248, 193, 92, 0.2); }
 100 | .key-warning {
 101 |   background: rgba(255, 59, 95, 0.08);
 102 |   border: 1px solid rgba(255, 59, 95, 0.2);
 103 |   border-radius: 10px;
 104 |   padding: 14px 18px;
 105 |   display: flex;
 106 |   gap: 12px;
 107 |   align-items: flex-start;
 108 |   margin-bottom: 28px;
 109 |   font-family: 'JetBrains Mono', monospace;
 110 |   font-size: 12px;
 111 |   color: #ff8ba0;
 112 | }
 113 | .quickstart {
 114 |   margin-bottom: 28px;
 115 | }
 116 | .quickstart-label {
 117 |   font-family: 'JetBrains Mono', monospace;
 118 |   font-size: 10px;
 119 |   font-weight: 800;
 120 |   letter-spacing: 0.15em;
 121 |   color: #95a0ba;
 122 |   text-transform: uppercase;
 123 |   margin-bottom: 10px;
 124 | }
 125 | .code-block {
 126 |   background: #06070b;
 127 |   border: 1px solid rgba(255, 255, 255, 0.07);
 128 |   border-radius: 10px;
 129 |   padding: 16px;
 130 |   font-family: 'JetBrains Mono', monospace;
 131 |   font-size: 12px;
 132 |   color: #5de4ff;
 133 |   overflow-x: auto;
 134 |   white-space: pre;
 135 | }
 136 | .action-links {
 137 |   display: flex;
 138 |   gap: 12px;
 139 |   flex-wrap: wrap;
 140 | }
 141 | .btn-primary {
 142 |   flex: 1;
 143 |   min-width: 160px;
 144 |   padding: 14px;
 145 |   background: #ff3b5f;
 146 |   border: none;
 147 |   border-radius: 10px;
 148 |   color: #eef2ff;
 149 |   font-family: 'JetBrains Mono', monospace;
 150 |   font-size: 13px;
 151 |   font-weight: 700;
 152 |   text-align: center;
 153 |   text-decoration: none;
 154 |   cursor: pointer;
 155 |   transition: all 0.2s;
 156 | }
 157 | .btn-primary:hover { background: #ff5577; color: #eef2ff; text-decoration: none; }
 158 | .btn-secondary {
 159 |   flex: 1;
 160 |   min-width: 160px;
 161 |   padding: 14px;
 162 |   background: transparent;
 163 |   border: 1px solid rgba(255, 255, 255, 0.15);
 164 |   border-radius: 10px;
 165 |   color: #eef2ff;
 166 |   font-family: 'JetBrains Mono', monospace;
 167 |   font-size: 13px;
 168 |   font-weight: 600;
 169 |   text-align: center;
 170 |   text-decoration: none;
 171 |   cursor: pointer;
 172 |   transition: all 0.2s;
 173 | }
 174 | .btn-secondary:hover { border-color: #f8c15c; color: #f8c15c; text-decoration: none; }
 175 | .error-card {
 176 |   background: rgba(255, 59, 95, 0.08);
 177 |   border: 1px solid rgba(255, 59, 95, 0.3);
 178 |   border-radius: 12px;
 179 |   padding: 24px;
 180 |   text-align: center;
 181 | }
 182 | .error-msg { color: #ff8ba0; font-family: 'JetBrains Mono', monospace; font-size: 14px; line-height: 1.6; }
 183 | </style>
 184 | {% endblock %}
 185 | {% block content %}
 186 | <div class="success-page">
 187 |   <div class="success-card">
 188 |     {% if api_key %}
 189 |     <div class="success-icon">⚡</div>
 190 |     <p class="success-eyebrow">Commander Terminal API</p>
 191 |     <h1 class="success-title">You're In The Network</h1>
 192 |     <p class="success-sub">Your API key is ready. 1,000 requests/hour. Real-time Bitcoin intelligence.</p>
 193 | 
 194 |     <div class="key-box">
 195 |       <div class="key-label">Your API Key — Save this now</div>
 196 |       <div class="key-value" id="apiKeyValue">{{ api_key }}</div>
 197 |       <div class="key-actions">
 198 |         <button class="btn-copy" onclick="copyKey()">Copy Key</button>
 199 |         <span id="copyStatus" style="display:none; font-family:monospace; font-size:12px; color:#89ffb8; align-self:center;">✓ Copied</span>
 200 |       </div>
 201 |     </div>
 202 | 
 203 |     <div class="key-warning">
 204 |       <span>⚠️</span>
 205 |       <span>This key will not be shown again. Save it to a password manager. If you lose it, go to <a href="/api/dashboard" style="color:#f8c15c;">your dashboard</a> to rotate it.</span>
 206 |     </div>
 207 | 
 208 |     <div class="quickstart">
 209 |       <div class="quickstart-label">Quick Start</div>
 210 |       <div class="code-block">curl https://protocolpulse.io/api/v2/terminal/topics \
 211 |   -H "X-API-Key: {{ api_key }}"</div>
 212 |     </div>
 213 | 
 214 |     <div class="action-links">
 215 |       <a href="/api/playground" class="btn-primary">Try Playground →</a>
 216 |       <a href="/api/dashboard" class="btn-secondary">Go to Dashboard</a>
 217 |     </div>
 218 | 
 219 |     {% elif error %}
 220 |     <div class="error-card">
 221 |       <div class="success-icon">⚠️</div>
 222 |       <p class="success-eyebrow">Subscription Issue</p>
 223 |       <p class="error-msg">{{ error }}</p>
 224 |       <p style="color:#95a0ba; font-size:13px; margin-top:16px; font-family:monospace;">
 225 |         {% if email %}Email: {{ email }} — {% endif %}
 226 |         Contact <a href="mailto:support@protocolpulse.io" style="color:#f8c15c;">support@protocolpulse.io</a>
 227 |       </p>
 228 |       <div class="action-links" style="margin-top:20px;">
 229 |         <a href="/api/dashboard" class="btn-primary">Check Dashboard</a>
 230 |         <a href="/premium" class="btn-secondary">Back to Premium</a>
 231 |       </div>
 232 |     </div>
 233 |     {% else %}
 234 |     <div class="success-icon">⏳</div>
 235 |     <p class="success-eyebrow">Processing</p>
 236 |     <h1 class="success-title">Provisioning Your Key</h1>
 237 |     <p class="success-sub">Your subscription is being activated. Check your email at <strong>{% if email %}{{ email }}{% else %}the address you used{% endif %}</strong> for your API key.</p>
 238 |     <div class="action-links" style="margin-top:20px;">
 239 |       <a href="/api/dashboard" class="btn-primary">Go to Dashboard</a>
 240 |       <a href="/premium" class="btn-secondary">Back to Premium</a>
 241 |     </div>
 242 |     {% endif %}
 243 |   </div>
 244 | </div>
 245 | <script>
 246 | function copyKey() {
 247 |   const key = document.getElementById('apiKeyValue');
 248 |   if (!key) return;
 249 |   navigator.clipboard.writeText(key.textContent.trim()).then(() => {
 250 |     const status = document.getElementById('copyStatus');
 251 |     if (status) {
 252 |       status.style.display = 'inline';
 253 |       setTimeout(() => { status.style.display = 'none'; }, 2500);
 254 |     }
 255 |   }).catch(() => {
 256 |     // fallback
 257 |     const range = document.createRange();
 258 |     range.selectNode(key);
 259 |     window.getSelection().removeAllRanges();
 260 |     window.getSelection().addRange(range);
 261 |     document.execCommand('copy');
 262 |     window.getSelection().removeAllRanges();
 263 |   });
 264 | }
 265 | </script>
 266 | {% endblock %}
 267 | 
```

### File: templates/media_unified.html (809 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Media Hub — Protocol Pulse Intelligence{% endblock %}
   3 | {% block meta_description %}Live Bitcoin intelligence terminal. Nostr feeds, on-chain data, sentiment analysis, and original podcast content.{% endblock %}
   4 | 
   5 | {% block head %}
   6 | <link rel="preconnect" href="https://fonts.googleapis.com">
   7 | <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   8 | <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Instrument+Serif&family=Geist+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
   9 | <link rel="stylesheet" href="/static/css/media_unified_v5.css">
  10 | {% endblock %}
  11 | 
  12 | {% block body_class %}mu-page{% endblock %}
  13 | 
  14 | {% block content %}
  15 | 
  16 | <!-- ════════════════════════════════════════════════════
  17 |      TELEMETRY RIBBON (sticky below nav)
  18 |      ════════════════════════════════════════════════════ -->
  19 | <div class="mu-telemetry" id="mu-telemetry">
  20 |   <div class="mu-telemetry-inner">
  21 |     <!-- Fee Rate -->
  22 |     <div class="mu-telem-metric">
  23 |       <span class="mu-telem-value" id="telem-fees" data-metric="fees">--</span>
  24 |       <canvas class="mu-sparkline" id="spark-fees" width="40" height="12"></canvas>
  25 |       <span class="mu-telem-label">sat/vB</span>
  26 |     </div>
  27 | 
  28 |     <div class="mu-telem-sep"></div>
  29 | 
  30 |     <!-- Mempool -->
  31 |     <div class="mu-telem-metric">
  32 |       <span class="mu-telem-value" id="telem-mempool" data-metric="mempool">--</span>
  33 |       <canvas class="mu-sparkline" id="spark-mempool" width="40" height="12"></canvas>
  34 |       <span class="mu-telem-label">MB</span>
  35 |     </div>
  36 | 
  37 |     <div class="mu-telem-sep"></div>
  38 | 
  39 |     <!-- Hashrate -->
  40 |     <div class="mu-telem-metric">
  41 |       <span class="mu-telem-value" id="telem-hashrate" data-metric="hashrate">--</span>
  42 |       <canvas class="mu-sparkline" id="spark-hashrate" width="40" height="12"></canvas>
  43 |       <span class="mu-telem-label">EH/s</span>
  44 |     </div>
  45 | 
  46 |     <div class="mu-telem-sep"></div>
  47 | 
  48 |     <!-- Block Height -->
  49 |     <div class="mu-telem-metric">
  50 |       <span class="mu-telem-value mu-telem-btc" id="telem-block" data-metric="block">--</span>
  51 |       <span class="mu-telem-label">BLOCK</span>
  52 |     </div>
  53 | 
  54 |     <div class="mu-telem-sep"></div>
  55 | 
  56 |     <!-- Signal Strength -->
  57 |     <div class="mu-telem-metric mu-telem-signal">
  58 |       <span class="mu-telem-label">SIGNAL</span>
  59 |       <span class="mu-telem-value" id="telem-signal">0</span>
  60 |       <div class="mu-signal-bar">
  61 |         <div class="mu-signal-fill" id="signal-fill"></div>
  62 |       </div>
  63 |     </div>
  64 | 
  65 |     <div class="mu-telem-sep"></div>
  66 | 
  67 |     <!-- X Spaces -->
  68 |     <div class="mu-telem-metric" title="X Spaces Sentiment">
  69 |       <span class="mu-telem-label">X SPACES</span>
  70 |       <span class="mu-telem-value" id="telem-xs-score" style="min-width:24px;">--</span>
  71 |       <span class="mu-telem-label" id="telem-xs-label" style="font-size:0.55rem;"></span>
  72 |     </div>
  73 | 
  74 |     <!-- Sentiment Track -->
  75 |     <div class="mu-sentiment-track-wrap">
  76 |       <span class="mu-sentiment-label-l">FEAR</span>
  77 |       <div class="mu-sentiment-track" id="sentiment-track">
  78 |         <div class="mu-sentiment-dot" id="sentiment-dot"></div>
  79 |       </div>
  80 |       <span class="mu-sentiment-label-r">GREED</span>
  81 |       <span class="mu-sentiment-num" id="sentiment-num">--</span>
  82 |     </div>
  83 |     <div class="mu-sentiment-why" id="sentiment-why"></div>
  84 | 
  85 |     <!-- Health Dots -->
  86 |     <div class="mu-health">
  87 |       <div class="mu-health-dot loading" id="health-nostr" title="Nostr"></div>
  88 |       <div class="mu-health-dot loading" id="health-telemetry" title="Telemetry"></div>
  89 |       <div class="mu-health-dot loading" id="health-sentiment" title="Sentiment"></div>
  90 |       <div class="mu-health-dot loading" id="health-xspaces" title="X Spaces"></div>
  91 |     </div>
  92 | 
  93 |     <!-- Cmd+K -->
  94 |     <div class="mu-cmdk-hint" id="cmd-k-hint">&#x2318;K</div>
  95 |   </div>
  96 | 
  97 |   <!-- Thermal border -->
  98 |   <div class="mu-thermal-border" id="thermal-border"></div>
  99 | </div>
 100 | 
 101 | <!-- ════════════════════════════════════════════════════
 102 |      HERO: Featured Media + Delta Card
 103 |      ════════════════════════════════════════════════════ -->
 104 | <section class="mu-hero">
 105 |   <!-- Featured — text IS the hero -->
 106 |   <div class="mu-featured" id="mu-featured">
 107 |     <div class="mu-featured-text" id="hero-text">
 108 |       <span class="mu-latest-label">LATEST</span>
 109 |       {% if latest_episodes and latest_episodes|length > 0 %}
 110 |         {% set ep = latest_episodes[0] %}
 111 |         <h1 class="mu-hero-title">{{ ep.title }}</h1>
 112 |         <div class="mu-hero-meta">
 113 |           <span>EP {{ loop.index if loop is defined else podcast_count }}</span>
 114 |           <span class="mu-hero-dot">&middot;</span>
 115 |           <span>PROTOCOL PULSE</span>
 116 |           <span class="mu-hero-dot">&middot;</span>
 117 |           <span>{{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}</span>
 118 |         </div>
 119 |         <button class="mu-play-btn" id="hero-play"
 120 |                 data-vid="{{ ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' }}">
 121 |           <span class="mu-play-icon">&#9654;</span>
 122 |           <span>PLAY</span>
 123 |         </button>
 124 |       {% else %}
 125 |         <h1 class="mu-hero-title">Protocol Pulse</h1>
 126 |         <div class="mu-hero-meta">
 127 |           <span>{{ podcast_count }} episodes</span>
 128 |         </div>
 129 |       {% endif %}
 130 |     </div>
 131 |     <!-- YouTube embed appears here on play click -->
 132 |     <div class="mu-featured-embed" id="hero-embed"></div>
 133 |   </div>
 134 | 
 135 |   <!-- Since You Were Gone -->
 136 |   <div class="mu-delta" id="mu-delta">
 137 |     <div class="mu-delta-count" id="delta-count">...</div>
 138 |     <div class="mu-delta-label" id="delta-label">Loading intelligence...</div>
 139 |     <div class="mu-delta-items" id="delta-items"></div>
 140 |     <button class="mu-delta-showme" id="delta-showme">&darr; SHOW ME</button>
 141 |   </div>
 142 | </section>
 143 | 
 144 | <!-- ════════════════════════════════════════════════════
 145 |      SIGNAL DASHBOARD: 2 Columns
 146 |      ════════════════════════════════════════════════════ -->
 147 | <section class="mu-signals" id="mu-signals">
 148 |   <!-- Left: Nostr + X Live -->
 149 |   <div class="mu-col">
 150 |     <div class="mu-col-header">
 151 |       <span class="mu-col-title">NOSTR + X LIVE</span>
 152 |       <span class="mu-col-source"><span class="mu-health-dot" id="health-nostr-col"></span></span>
 153 |     </div>
 154 |     <!-- D4: Relay Status Bar -->
 155 |     <div class="mu-relay-status-bar" id="relay-status-bar">
 156 |       <div class="mu-relay-item" data-relay="relay.damus.io">
 157 |         <div class="mu-relay-dot" style="background:#555"></div>
 158 |         <span class="mu-relay-name">damus</span>
 159 |         <span class="mu-relay-status">OFFLINE</span>
 160 |         <span class="mu-relay-count">0 notes</span>
 161 |       </div>
 162 |       <div class="mu-relay-item" data-relay="nos.lol">
 163 |         <div class="mu-relay-dot" style="background:#555"></div>
 164 |         <span class="mu-relay-name">nos.lol</span>
 165 |         <span class="mu-relay-status">OFFLINE</span>
 166 |         <span class="mu-relay-count">0 notes</span>
 167 |       </div>
 168 |       <div class="mu-relay-item" data-relay="relay.nostr.band">
 169 |         <div class="mu-relay-dot" style="background:#555"></div>
 170 |         <span class="mu-relay-name">nostr.band</span>
 171 |         <span class="mu-relay-status">OFFLINE</span>
 172 |         <span class="mu-relay-count">0 notes</span>
 173 |       </div>
 174 |     </div>
 175 |     <div class="mu-col-feed" id="nostr-feed"></div>
 176 |     <div class="mu-col-count" id="nostr-count">0 notes</div>
 177 |   </div>
 178 | 
 179 |   <div class="mu-col-divider"></div>
 180 | 
 181 |   <!-- Right: Verified Highlights -->
 182 |   <div class="mu-col">
 183 |     <div class="mu-col-header">
 184 |       <span class="mu-col-title">VERIFIED HIGHLIGHTS</span>
 185 |       <span class="mu-col-source">partner channels <span class="mu-health-dot connected" id="health-highlights-col"></span></span>
 186 |     </div>
 187 |     <div class="mu-col-feed" id="highlights-feed">
 188 |       {% if ssr_highlights %}
 189 |         {% for h in ssr_highlights %}
 190 |         <div class="mu-highlight-item">
 191 |           <div class="mu-highlight-quote">&ldquo;{{ h.excerpt[:180] }}&rdquo;</div>
 192 |           <div class="mu-highlight-source">&mdash; {{ h.source }}{% if h.direction == 'bullish' %} <span style="color:#22c55e">BULLISH</span>{% elif h.direction == 'bearish' %} <span style="color:#dc2626">BEARISH</span>{% endif %}</div>
 193 |         </div>
 194 |         {% endfor %}
 195 |       {% endif %}
 196 |     </div>
 197 |   </div>
 198 | </section>
 199 | 
 200 | <!-- ════════════════════════════════════════════════════
 201 |      SIGNAL STRENGTH GAUGE (Phase 2)
 202 |      ════════════════════════════════════════════════════ -->
 203 | <section class="mu-section mu-signal-section" id="mu-signal-section">
 204 |   <div class="mu-section-head">
 205 |     <h2 class="mu-section-title">SIGNAL STRENGTH</h2>
 206 |     <span class="mu-section-sub">Composite intelligence score — live</span>
 207 |   </div>
 208 |   <div class="mu-signal-gauge-wrap">
 209 |     <div id="signal-strength-gauge">
 210 |       <div class="mu-gauge-ring" style="--score:50%;--color:#E67E22">
 211 |         <div class="mu-gauge-inner">
 212 |           <div class="mu-gauge-score">--</div>
 213 |           <div class="mu-gauge-label">SIGNAL</div>
 214 |           <div class="mu-gauge-level">LOADING</div>
 215 |         </div>
 216 |       </div>
 217 |     </div>
 218 |     <div class="mu-signal-breakdown" id="signal-breakdown">
 219 |       <div class="mu-sig-row">
 220 |         <span class="mu-sig-key">SENTIMENT</span>
 221 |         <span class="mu-sig-val" id="sig-sentiment">--</span>
 222 |         <span class="mu-sig-weight">70%</span>
 223 |       </div>
 224 |       <div class="mu-sig-row">
 225 |         <span class="mu-sig-key">X SPACES</span>
 226 |         <span class="mu-sig-val" id="sig-spaces">--</span>
 227 |         <span class="mu-sig-weight">30%</span>
 228 |       </div>
 229 |       <div class="mu-sig-row mu-sig-total">
 230 |         <span class="mu-sig-key">COMPOSITE</span>
 231 |         <span class="mu-sig-val" id="sig-composite">--</span>
 232 |         <span class="mu-sig-weight">&nbsp;</span>
 233 |       </div>
 234 |     </div>
 235 |   </div>
 236 | </section>
 237 | 
 238 | <!-- ════════════════════════════════════════════════════
 239 |      REDDIT PULSE
 240 |      ════════════════════════════════════════════════════ -->
 241 | <section class="mu-section" id="mu-reddit">
 242 |   <div class="mu-section-head">
 243 |     <h2 class="mu-section-title">REDDIT PULSE</h2>
 244 |     <span class="mu-section-sub">r/bitcoin &middot; live</span>
 245 |   </div>
 246 |   <div class="mu-reddit-feed" id="reddit-feed"></div>
 247 | </section>
 248 | 
 249 | <!-- ════════════════════════════════════════════════════
 250 |      PARTNER CHANNELS TODAY
 251 |      ════════════════════════════════════════════════════ -->
 252 | <section class="mu-section" id="mu-partners">
 253 |   <div class="mu-section-head">
 254 |     <h2 class="mu-section-title">PARTNER CHANNELS TODAY</h2>
 255 |     <span class="mu-section-sub">{{ series_count }} channels tracked</span>
 256 |   </div>
 257 |   <div class="mu-partner-rail" id="partner-rail"></div>
 258 | </section>
 259 | 
 260 | <!-- ════════════════════════════════════════════════════
 261 |      ORIGINAL SERIES
 262 |      ════════════════════════════════════════════════════ -->
 263 | <section class="mu-section" id="mu-series">
 264 |   <div class="mu-section-head">
 265 |     <h2 class="mu-section-title">ORIGINAL SERIES</h2>
 266 |   </div>
 267 |   <div class="mu-series-grid">
 268 |     {% for s in series_list %}
 269 |     <a class="mu-series-item" href="https://youtube.com/watch?v={{ s.first_id }}" target="_blank" rel="noopener"
 270 |        data-thumb="https://img.youtube.com/vi/{{ s.first_id }}/maxresdefault.jpg">
 271 |       <div class="mu-series-name">{{ s.title }}</div>
 272 |       <div class="mu-series-sub">{{ s.description|upper if s.description else '' }}</div>
 273 |       <div class="mu-series-count">{{ s.ep_count }} episodes</div>
 274 |     </a>
 275 |     {% endfor %}
 276 |   </div>
 277 | </section>
 278 | 
 279 | <!-- ════════════════════════════════════════════════════
 280 |      LATEST EPISODES
 281 |      ════════════════════════════════════════════════════ -->
 282 | <section class="mu-section" id="mu-episodes">
 283 |   <div class="mu-section-head">
 284 |     <h2 class="mu-section-title">LATEST EPISODES</h2>
 285 |     <span class="mu-section-sub">{{ podcast_count }} episodes</span>
 286 |   </div>
 287 |   <div class="mu-ep-filters">
 288 |     <button class="mu-chip active" data-filter="all">All</button>
 289 |     <button class="mu-chip" data-filter="episodes">Episodes</button>
 290 |     <button class="mu-chip" data-filter="clips">Clips</button>
 291 |     <button class="mu-chip" data-filter="briefings">Briefings</button>
 292 |   </div>
 293 |   <div class="mu-ep-grid">
 294 |     {% for ep in latest_episodes[:12] %}
 295 |     {% set vid_id = ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' %}
 296 |     <a class="mu-ep-item" href="https://youtube.com/watch?v={{ vid_id }}" target="_blank" rel="noopener">
 297 |       <div class="mu-ep-thumb">
 298 |         <img src="https://img.youtube.com/vi/{{ vid_id }}/mqdefault.jpg" alt="{{ ep.title }}" loading="lazy" width="320" height="180">
 299 |       </div>
 300 |       <div class="mu-ep-info">
 301 |         <div class="mu-ep-title">{{ ep.title }}</div>
 302 |         <div class="mu-ep-meta">
 303 |           {{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}
 304 |           {% if ep.host %} &middot; {{ ep.host }}{% endif %}
 305 |         </div>
 306 |       </div>
 307 |     </a>
 308 |     {% endfor %}
 309 |   </div>
 310 | </section>
 311 | 
 312 | <!-- ════════════════════════════════════════════════════
 313 |      THE LIBRARY
 314 |      ════════════════════════════════════════════════════ -->
 315 | <section class="mu-section" id="mu-library">
 316 |   <div class="mu-section-head">
 317 |     <h2 class="mu-section-title">THE LIBRARY</h2>
 318 |     <span class="mu-section-sub">Curated reading for sovereign minds</span>
 319 |   </div>
 320 | 
 321 |   <!-- Leaderboard + Rising Stars -->
 322 |   <div class="mu-lib-top">
 323 |     <div class="mu-lib-leaderboard">
 324 |       <div class="mu-lib-subtitle">LEADERBOARD</div>
 325 |       <div class="mu-lb-item" data-rank="1">
 326 |         <span class="mu-lb-rank">#1</span>
 327 |         <span class="mu-lb-title">The Bitcoin Standard</span>
 328 |         <span class="mu-lb-dot">&middot;</span>
 329 |         <span class="mu-lb-author">Saifedean Ammous</span>
 330 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:100%"></div></div>
 331 |         <button class="mu-vote-btn" data-book="bitcoin-standard">&#128077;</button>
 332 |         <span class="mu-vote-count" data-book="bitcoin-standard">0</span>
 333 |       </div>
 334 |       <div class="mu-lb-item" data-rank="2">
 335 |         <span class="mu-lb-rank">#2</span>
 336 |         <span class="mu-lb-title">Broken Money</span>
 337 |         <span class="mu-lb-dot">&middot;</span>
 338 |         <span class="mu-lb-author">Lyn Alden</span>
 339 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:82%"></div></div>
 340 |         <button class="mu-vote-btn" data-book="broken-money">&#128077;</button>
 341 |         <span class="mu-vote-count" data-book="broken-money">0</span>
 342 |       </div>
 343 |       <div class="mu-lb-item" data-rank="3">
 344 |         <span class="mu-lb-rank">#3</span>
 345 |         <span class="mu-lb-title">The Sovereign Individual</span>
 346 |         <span class="mu-lb-dot">&middot;</span>
 347 |         <span class="mu-lb-author">Davidson &amp; Rees-Mogg</span>
 348 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:68%"></div></div>
 349 |         <button class="mu-vote-btn" data-book="sovereign-individual">&#128077;</button>
 350 |         <span class="mu-vote-count" data-book="sovereign-individual">0</span>
 351 |       </div>
 352 |       <div class="mu-lb-item" data-rank="4">
 353 |         <span class="mu-lb-rank">#4</span>
 354 |         <span class="mu-lb-title">Mastering Bitcoin</span>
 355 |         <span class="mu-lb-dot">&middot;</span>
 356 |         <span class="mu-lb-author">Andreas Antonopoulos</span>
 357 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:55%"></div></div>
 358 |         <button class="mu-vote-btn" data-book="mastering-bitcoin">&#128077;</button>
 359 |         <span class="mu-vote-count" data-book="mastering-bitcoin">0</span>
 360 |       </div>
 361 |     </div>
 362 | 
 363 |     <div class="mu-lib-rising">
 364 |       <div class="mu-lib-subtitle">RISING STARS</div>
 365 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Resistance Money &middot; Andrew M. Bailey</div>
 366 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Bitcoin is Venice &middot; Allen Farrington</div>
 367 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Check Your Financial Privilege &middot; Alex Gladstein</div>
 368 |     </div>
 369 |   </div>
 370 | 
 371 |   <!-- Learning Paths -->
 372 |   <div class="mu-lib-paths">
 373 |     <div class="mu-lib-subtitle">LEARNING PATHS</div>
 374 |     <div class="mu-paths-grid">
 375 |       <div class="mu-path">
 376 |         <div class="mu-path-name">UNDERSTAND MONEY</div>
 377 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1119473861" target="_blank" rel="noopener">The Bitcoin Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 378 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544526474" target="_blank" rel="noopener">The Fiat Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 379 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0CN14FKHF" target="_blank" rel="noopener">Broken Money <span class="mu-path-author">&middot; Lyn Alden</span></a>
 380 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1999257405" target="_blank" rel="noopener">The Price of Tomorrow <span class="mu-path-author">&middot; Jeff Booth</span></a>
 381 |       </div>
 382 |       <div class="mu-path">
 383 |         <div class="mu-path-name">UNDERSTAND BITCOIN</div>
 384 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1098150090" target="_blank" rel="noopener">Mastering Bitcoin <span class="mu-path-author">&middot; Andreas Antonopoulos</span></a>
 385 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B07MWGP64R" target="_blank" rel="noopener">Inventing Bitcoin <span class="mu-path-author">&middot; Yan Pritzker</span></a>
 386 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B08YQMC2WM" target="_blank" rel="noopener">The Blocksize War <span class="mu-path-author">&middot; Jonathan Bier</span></a>
 387 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0B3L61JYN" target="_blank" rel="noopener">The Genesis Book <span class="mu-path-author">&middot; Aaron van Wirdum</span></a>
 388 |       </div>
 389 |       <div class="mu-path">
 390 |         <div class="mu-path-name">UNDERSTAND FREEDOM</div>
 391 |         <a class="mu-path-book" href="https://www.amazon.com/dp/0684832720" target="_blank" rel="noopener">The Sovereign Individual <span class="mu-path-author">&middot; Davidson &amp; Rees-Mogg</span></a>
 392 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544542895" target="_blank" rel="noopener">Softwar <span class="mu-path-author">&middot; Jason Lowery</span></a>
 393 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09C4GLPYX" target="_blank" rel="noopener">Thank God for Bitcoin <span class="mu-path-author">&middot; Jimmy Song et al.</span></a>
 394 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09KLPNBPC" target="_blank" rel="noopener">Bitcoin is Venice <span class="mu-path-author">&middot; Allen Farrington</span></a>
 395 |       </div>
 396 |     </div>
 397 |   </div>
 398 | 
 399 |   <!-- Full Library (collapsed by default) -->
 400 |   <button class="mu-lib-toggle" id="lib-toggle">&darr; VIEW FULL LIBRARY</button>
 401 |   <div class="mu-lib-full" id="lib-full">
 402 |     <div class="mu-lib-grid">
 403 |       {% for book in all_books %}
 404 |       <a class="mu-lib-book" href="{{ book.amazon_url }}" target="_blank" rel="noopener">
 405 |         <div class="mu-lib-cover" style="background:{{ book.color|default('#222') }}">
 406 |           <span>{{ book.title[:40] }}</span>
 407 |         </div>
 408 |         <div class="mu-lib-book-title">{{ book.title }}</div>
 409 |         <div class="mu-lib-book-author">{{ book.author }}</div>
 410 |         <button class="mu-vote-btn" data-book="{{ book.title|lower|replace(' ','-') }}">&#128077;</button>
 411 |         <span class="mu-vote-count" data-book="{{ book.title|lower|replace(' ','-') }}">0</span>
 412 |       </a>
 413 |       {% endfor %}
 414 |     </div>
 415 |   </div>
 416 | </section>
 417 | 
 418 | <!-- ════════════════════════════════════════════════════
 419 |      NEWSLETTER CTA
 420 |      ════════════════════════════════════════════════════ -->
 421 | <section class="mu-newsletter" id="mu-newsletter">
 422 |   <h2 class="mu-nl-title">Sovereign Intel Briefing</h2>
 423 |   <p class="mu-nl-sub">Daily Bitcoin intelligence. No noise. No ads. Delivered before markets open.</p>
 424 |   <div class="mu-nl-form">
 425 |     <input type="email" placeholder="your@email.com" id="newsletter-email" autocomplete="email">
 426 |     <button id="newsletter-submit">Subscribe</button>
 427 |   </div>
 428 | </section>
 429 | 
 430 | <!-- ════════════════════════════════════════════════════
 431 |      COMMAND PALETTE (Cmd+K)
 432 |      ════════════════════════════════════════════════════ -->
 433 | <div class="mu-cmd-overlay" id="cmd-overlay">
 434 |   <div class="mu-cmd-box">
 435 |     <div class="mu-cmd-prompt">
 436 |       <span class="mu-cmd-caret">&gt;</span>
 437 |       <input class="mu-cmd-input" id="cmd-input" placeholder="" autocomplete="off" spellcheck="false">
 438 |     </div>
 439 |     <div class="mu-cmd-results" id="cmd-results"></div>
 440 |     <div class="mu-cmd-footer">Press &uarr;&darr; to navigate &middot; Enter to select &middot; Esc to close</div>
 441 |   </div>
 442 | </div>
 443 | 
 444 | <!-- ════════════════════════════════════════════════════
 445 |      AUDIO BAR (floating, hidden until active)
 446 |      ════════════════════════════════════════════════════ -->
 447 | <div class="mu-audio-bar" id="audio-bar">
 448 |   <button class="mu-ab-play" id="ab-play">&#9654;</button>
 449 |   <span class="mu-ab-info" id="ab-info"></span>
 450 |   <div class="mu-ab-progress">
 451 |     <div class="mu-ab-track">
 452 |       <div class="mu-ab-fill" id="ab-fill"></div>
 453 |       <div class="mu-ab-dot" id="ab-dot"></div>
 454 |     </div>
 455 |   </div>
 456 |   <span class="mu-ab-time" id="ab-time">0:00 / 0:00</span>
 457 |   <button class="mu-ab-speed" id="ab-speed">1&times;</button>
 458 | </div>
 459 | 
 460 | <!-- D5: Health Strip -->
 461 | <div id="health-strip" class="mu-health-strip"></div>
 462 | 
 463 | {% endblock %}
 464 | 
 465 | {% block scripts %}
 466 | <script src="/static/js/media_unified_v5.js"></script>
 467 | <script>
 468 | function subscribeNewsletter() {
 469 |   const email = document.getElementById('newsletter-email').value;
 470 |   if (!email || !email.includes('@')) { alert('Enter a valid email'); return; }
 471 |   fetch('/api/newsletter/subscribe', {
 472 |     method: 'POST',
 473 |     headers: {'Content-Type': 'application/json'},
 474 |     body: JSON.stringify({email: email})
 475 |   }).then(r => r.json()).then(d => {
 476 |     if (d.success) alert('Subscribed! Check your inbox.');
 477 |     else alert(d.message || 'Subscription failed');
 478 |   }).catch(() => alert('Network error — try again'));
 479 | }
 480 | document.getElementById('newsletter-submit')?.addEventListener('click', subscribeNewsletter);
 481 | 
 482 | // Phase 2: X Spaces + telemetry wired in media_p2_init below
 483 | </script>
 484 | 
 485 | <style>
 486 | /* ── D4: Relay Status Bar ─────────────────────── */
 487 | .mu-relay-status-bar {
 488 |   display: flex; gap: 8px; padding: 6px 12px;
 489 |   background: rgba(247,147,26,0.04); border-bottom: 1px solid #1a1a1a;
 490 |   flex-wrap: wrap;
 491 | }
 492 | .mu-relay-item {
 493 |   display: flex; align-items: center; gap: 5px;
 494 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 495 | }
 496 | .mu-relay-dot {
 497 |   width: 7px; height: 7px; border-radius: 50%;
 498 |   animation: mu-pulse 2s infinite;
 499 | }
 500 | .mu-relay-name { color: #888; letter-spacing: 1px; }
 501 | .mu-relay-status { color: #555; font-size: 8px; }
 502 | .mu-relay-count { color: #444; font-size: 8px; }
 503 | 
 504 | /* ── D3: Signal Strength Gauge ────────────────── */
 505 | .mu-signal-section { padding: 24px 0; }
 506 | .mu-signal-gauge-wrap {
 507 |   display: flex; align-items: center; gap: 40px;
 508 |   padding: 20px 0; flex-wrap: wrap;
 509 | }
 510 | #signal-strength-gauge { flex-shrink: 0; }
 511 | .mu-gauge-ring {
 512 |   position: relative; width: 140px; height: 140px;
 513 |   border-radius: 50%;
 514 |   background: conic-gradient(var(--color) var(--score), #1a1a1a 0);
 515 |   display: flex; align-items: center; justify-content: center;
 516 |   box-shadow: 0 0 24px color-mix(in srgb, var(--color) 30%, transparent);
 517 | }
 518 | .mu-gauge-inner {
 519 |   width: 100px; height: 100px; border-radius: 50%;
 520 |   background: #0a0a0a;
 521 |   display: flex; flex-direction: column;
 522 |   align-items: center; justify-content: center; gap: 2px;
 523 | }
 524 | .mu-gauge-score {
 525 |   font-family: 'Geist Mono', monospace; font-size: 30px;
 526 |   font-weight: 900; color: var(--color); line-height: 1;
 527 | }
 528 | .mu-gauge-label {
 529 |   font-family: 'Geist Mono', monospace; font-size: 8px;
 530 |   color: #555; letter-spacing: 2px;
 531 | }
 532 | .mu-gauge-level {
 533 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 534 |   font-weight: 700; color: var(--color);
 535 | }
 536 | .mu-signal-breakdown {
 537 |   display: flex; flex-direction: column; gap: 10px; min-width: 220px;
 538 | }
 539 | .mu-sig-row {
 540 |   display: flex; gap: 8px; align-items: center;
 541 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 542 | }
 543 | .mu-sig-key { color: #555; letter-spacing: 1px; min-width: 90px; }
 544 | .mu-sig-val { color: #F7931A; font-weight: 700; min-width: 32px; }
 545 | .mu-sig-weight { color: #333; font-size: 9px; }
 546 | .mu-sig-total .mu-sig-key { color: #888; }
 547 | .mu-sig-total .mu-sig-val { color: #fff; font-size: 14px; }
 548 | 
 549 | /* ── D5: Health Strip ─────────────────────────── */
 550 | .mu-health-strip {
 551 |   position: fixed; bottom: 0; left: 0; right: 0;
 552 |   height: 30px; background: #050505;
 553 |   border-top: 1px solid #1a1a1a;
 554 |   display: flex; align-items: center;
 555 |   padding: 0 16px; gap: 20px; z-index: 9999;
 556 |   overflow-x: auto; overflow-y: hidden;
 557 | }
 558 | .mu-hs-item { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
 559 | .mu-hs-dot {
 560 |   width: 7px; height: 7px; border-radius: 50%;
 561 |   animation: mu-pulse 2s infinite;
 562 | }
 563 | .mu-hs-name {
 564 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 565 |   color: #555; letter-spacing: 1px;
 566 | }
 567 | .mu-hs-lat {
 568 |   font-family: 'Geist Mono', monospace; font-size: 8px; color: #333;
 569 | }
 570 | @keyframes mu-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
 571 | 
 572 | /* Bottom padding so health strip doesn't cover content */
 573 | .mu-page { padding-bottom: 38px; }
 574 | </style>
 575 | 
 576 | <script>
 577 | // ═══════════════════════════════════════════════════════
 578 | // MEDIA UNIFIED — PHASE 2 RUNTIME
 579 | // D1: Clean API wiring  D2: Live telemetry  D3: Signal gauge
 580 | // D4: Nostr relay panel  D5: Health strip
 581 | // ═══════════════════════════════════════════════════════
 582 | 
 583 | (function() {
 584 |   'use strict';
 585 | 
 586 |   // ── Cache ────────────────────────────────────────────
 587 |   var _cache = { sentiment: null, spaces: null, tradfi: null };
 588 | 
 589 |   // ── D1 + D2: Live Telemetry Wiring ──────────────────
 590 |   async function fetchSentiment() {
 591 |     try {
 592 |       var r = await fetch('/api/media/sentiment');
 593 |       var d = await r.json();
 594 |       _cache.sentiment = d;
 595 |       return d;
 596 |     } catch(e) {
 597 |       console.warn('[P2] sentiment fetch failed:', e);
 598 |       return _cache.sentiment || { composite_score: null, label: 'OFFLINE' };
 599 |     }
 600 |   }
 601 | 
 602 |   async function fetchSpaces() {
 603 |     try {
 604 |       var r = await fetch('/api/spaces/live');
 605 |       var d = await r.json();
 606 |       _cache.spaces = d;
 607 |       return d;
 608 |     } catch(e) {
 609 |       console.warn('[P2] spaces fetch failed:', e);
 610 |       return _cache.spaces || { spaces: [], score: 0, label: 'OFFLINE' };
 611 |     }
 612 |   }
 613 | 
 614 |   async function fetchTradfi() {
 615 |     try {
 616 |       var r = await fetch('/api/tradfi/signals');
 617 |       var d = await r.json();
 618 |       _cache.tradfi = d;
 619 |       return d;
 620 |     } catch(e) {
 621 |       return _cache.tradfi || null;
 622 |     }
 623 |   }
 624 | 
 625 |   // ── D3: Signal Strength Gauge Renderer ──────────────
 626 |   function computeSignalStrength(sentData, spacesData) {
 627 |     var sentScore = (sentData && sentData.composite_score != null)
 628 |       ? parseFloat(sentData.composite_score) : 50;
 629 |     var spacesCount = (spacesData && spacesData.spaces)
 630 |       ? spacesData.spaces.length : 0;
 631 |     var spacesScore = Math.min(spacesCount * 10, 100);
 632 |     return Math.round(sentScore * 0.7 + spacesScore * 0.3);
 633 |   }
 634 | 
 635 |   function renderSignalGauge(score, sentScore, spacesScore) {
 636 |     var el = document.getElementById('signal-strength-gauge');
 637 |     if (!el) return;
 638 |     var level = score >= 70 ? 'HIGH' : score >= 40 ? 'MODERATE' : 'LOW';
 639 |     var color = score >= 70 ? '#F7931A' : score >= 40 ? '#E67E22' : '#666';
 640 |     el.innerHTML =
 641 |       '<div class="mu-gauge-ring" style="--score:' + score + '%;--color:' + color + '">' +
 642 |         '<div class="mu-gauge-inner">' +
 643 |           '<div class="mu-gauge-score">' + score + '</div>' +
 644 |           '<div class="mu-gauge-label">SIGNAL</div>' +
 645 |           '<div class="mu-gauge-level">' + level + '</div>' +
 646 |         '</div>' +
 647 |       '</div>';
 648 |     // Update breakdown
 649 |     var sEl = document.getElementById('sig-sentiment');
 650 |     var spEl = document.getElementById('sig-spaces');
 651 |     var cEl = document.getElementById('sig-composite');
 652 |     if (sEl) sEl.textContent = Math.round(sentScore);
 653 |     if (spEl) spEl.textContent = Math.round(Math.min((spacesScore||0)*10,100));
 654 |     if (cEl) cEl.textContent = score;
 655 |   }
 656 | 
 657 |   // ── D4: Nostr Relay Status Panel Updater ────────────
 658 |   // Hook into the existing RelayManager to sync relay dots
 659 |   function syncRelayStatusBar() {
 660 |     if (!window.relayManager || !window.relayManager.sockets) return;
 661 |     var sockets = window.relayManager.sockets;
 662 |     Object.keys(sockets).forEach(function(url) {
 663 |       var ws = sockets[url];
 664 |       var relayName = url.replace('wss://','').split('/')[0];
 665 |       var el = document.querySelector('[data-relay="' + relayName + '"]');
 666 |       if (!el) return;
 667 |       var dot = el.querySelector('.mu-relay-dot');
 668 |       var statusEl = el.querySelector('.mu-relay-status');
 669 |       var countEl = el.querySelector('.mu-relay-count');
 670 |       if (!dot || !statusEl) return;
 671 |       var rs = ws.readyState;
 672 |       if (rs === 1) { // OPEN
 673 |         dot.style.background = '#F7931A';
 674 |         statusEl.textContent = 'LIVE';
 675 |         statusEl.style.color = '#F7931A';
 676 |       } else if (rs === 0) { // CONNECTING
 677 |         dot.style.background = '#E67E22';
 678 |         statusEl.textContent = 'CONNECTING';
 679 |         statusEl.style.color = '#E67E22';
 680 |       } else {
 681 |         dot.style.background = '#444';
 682 |         statusEl.textContent = 'OFFLINE';
 683 |         statusEl.style.color = '#444';
 684 |       }
 685 |     });
 686 |     // Sync note counts from state
 687 |     if (window.state && window.state.nostrNotes) {
 688 |       var byRelay = {};
 689 |       window.state.nostrNotes.forEach(function(n) {
 690 |         if (n.relay) byRelay[n.relay] = (byRelay[n.relay]||0) + 1;
 691 |       });
 692 |       Object.keys(byRelay).forEach(function(url) {
 693 |         var relayName = url.replace('wss://','').split('/')[0];
 694 |         var el = document.querySelector('[data-relay="' + relayName + '"]');
 695 |         if (!el) return;
 696 |         var countEl = el.querySelector('.mu-relay-count');
 697 |         if (countEl) countEl.textContent = byRelay[url] + ' notes';
 698 |       });
 699 |     }
 700 |   }
 701 | 
 702 |   // ── X Spaces Telemetry Display (D1 replacement) ─────
 703 |   function updateXSpacesTelemetry(spacesData) {
 704 |     var xs = spacesData || {};
 705 |     var xsScore = xs.score != null ? xs.score : (xs.x_spaces ? xs.x_spaces.score : null);
 706 |     var xsLabel = xs.label || (xs.x_spaces ? xs.x_spaces.label : '') || '';
 707 |     var activeCount = xs.spaces ? xs.spaces.length : (xs.active_count || 0);
 708 | 
 709 |     var sc = document.getElementById('telem-xs-score');
 710 |     var lb = document.getElementById('telem-xs-label');
 711 |     var dot = document.getElementById('health-xspaces');
 712 |     if (sc && xsScore != null) sc.textContent = xsScore;
 713 |     if (lb && xsLabel) {
 714 |       lb.textContent = xsLabel;
 715 |       lb.style.color = xsLabel === 'BULLISH' ? '#22c55e'
 716 |                      : xsLabel === 'BEARISH' ? '#ef4444' : '#888';
 717 |     }
 718 |     if (dot) {
 719 |       dot.classList.remove('loading');
 720 |       dot.classList.add(activeCount > 0 ? 'connected' : 'error');
 721 |     }
 722 | 
 723 |     // Provide blend shim to existing signal engine
 724 |     window._ppBlendXSpaces = function(baseScore) {
 725 |       if (xsScore != null) return Math.round(baseScore * 0.7 + xsScore * 0.3);
 726 |       return baseScore;
 727 |     };
 728 |   }
 729 | 
 730 |   // ── D2: Master 30s Telemetry Poll ───────────────────
 731 |   async function updateTelemetry() {
 732 |     var results = await Promise.allSettled([
 733 |       fetchSentiment(),
 734 |       fetchSpaces(),
 735 |       fetchTradfi()
 736 |     ]);
 737 | 
 738 |     var sentData  = results[0].status === 'fulfilled' ? results[0].value : (_cache.sentiment || {});
 739 |     var spacesData = results[1].status === 'fulfilled' ? results[1].value : (_cache.spaces || {});
 740 | 
 741 |     // Update X Spaces display
 742 |     updateXSpacesTelemetry(spacesData);
 743 | 
 744 |     // D3: Compute + render Signal Strength gauge
 745 |     var spacesCount = spacesData.spaces ? spacesData.spaces.length : 0;
 746 |     var sentScore = sentData.composite_score != null ? parseFloat(sentData.composite_score) : 50;
 747 |     var score = computeSignalStrength(sentData, spacesData);
 748 |     renderSignalGauge(score, sentScore, spacesCount);
 749 | 
 750 |     // D4: Sync relay status bar
 751 |     syncRelayStatusBar();
 752 |   }
 753 | 
 754 |   // ── D5: Health Strip ─────────────────────────────────
 755 |   var P2_SERVICES = [
 756 |     { name: 'PIPELINE', url: 'https://relay.protocolpulse.io/health' },
 757 |     { name: 'ORACLE',   url: 'https://avatar.protocolpulse.io/health' },
 758 |     { name: 'REPLIT',   url: '/api/health' },
 759 |     { name: 'SPACES',   url: '/api/spaces/live' },
 760 |     { name: 'TRADFI',   url: '/api/tradfi/signals' },
 761 |   ];
 762 | 
 763 |   async function checkService(svc) {
 764 |     var start = Date.now();
 765 |     try {
 766 |       var r = await Promise.race([
 767 |         fetch(svc.url, { method: 'HEAD', cache: 'no-store' }),
 768 |         new Promise(function(_, rej) { setTimeout(function(){ rej(new Error('timeout')); }, 5000); })
 769 |       ]);
 770 |       return { status: r.ok ? 'UP' : 'DEGRADED', lat: Date.now() - start };
 771 |     } catch(e) {
 772 |       return { status: 'DOWN', lat: null };
 773 |     }
 774 |   }
 775 | 
 776 |   async function updateHealthStrip() {
 777 |     var strip = document.getElementById('health-strip');
 778 |     if (!strip) return;
 779 |     var results = await Promise.allSettled(P2_SERVICES.map(checkService));
 780 |     strip.innerHTML = P2_SERVICES.map(function(svc, i) {
 781 |       var r = (results[i].status === 'fulfilled' ? results[i].value : null) || { status: 'UNKNOWN', lat: null };
 782 |       var color = r.status === 'UP' ? '#27AE60' : r.status === 'DEGRADED' ? '#E67E22' : '#444';
 783 |       var lat = r.lat ? r.lat + 'ms' : '--';
 784 |       return '<div class="mu-hs-item">' +
 785 |         '<div class="mu-hs-dot" style="background:' + color + '"></div>' +
 786 |         '<span class="mu-hs-name">' + svc.name + '</span>' +
 787 |         '<span class="mu-hs-lat">' + lat + '</span>' +
 788 |       '</div>';
 789 |     }).join('');
 790 |   }
 791 | 
 792 |   // ── BOOT ─────────────────────────────────────────────
 793 |   document.addEventListener('DOMContentLoaded', function() {
 794 |     // D2+D3: initial poll + 30s interval
 795 |     updateTelemetry();
 796 |     setInterval(updateTelemetry, 30000);
 797 | 
 798 |     // D4: Relay status sync every 5s
 799 |     setInterval(syncRelayStatusBar, 5000);
 800 | 
 801 |     // D5: Health strip initial + 60s interval
 802 |     updateHealthStrip();
 803 |     setInterval(updateHealthStrip, 60000);
 804 |   });
 805 | 
 806 | })();
 807 | </script>
 808 | {% endblock %}
 809 | 
```

### File: video_pipeline_v3/dual_host_tts.py (372 lines)
```
   1 | #!/usr/bin/env python3
   2 | """dual_host_tts.py — Single-host TTS engine for Pulse Check.
   3 | 
   4 | Generates audio using ElevenLabs TTS.
   5 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) — PBX approved single narrator at 1.10x speed.
   6 | Both host=1 and host=2 entries route to Mark (single voice, no gender swap).
   7 | 
   8 | Usage:
   9 |     from dual_host_tts import generate_dialogue_audio
  10 | 
  11 |     dialogue = [
  12 |         {"host": 1, "text": "So Saylor just dropped another banger..."},
  13 |         {"host": 2, "text": "Let's roll the clip."},
  14 |         {"host": "CLIP", "duration": 30, "source": "@MicroStrategy"},
  15 |         {"host": 2, "text": "Ok here's what blows my mind about this..."},
  16 |         {"host": 1, "text": "Right, and if you think about it..."},
  17 |     ]
  18 | 
  19 |     result = generate_dialogue_audio(dialogue, output_dir="output/")
  20 |     # Returns: {
  21 |     #   "lines": [...],
  22 |     #   "full": "output/full_dialogue.m4a",
  23 |     #   "total_duration": 45.0,
  24 |     # }
  25 | """
  26 | import os
  27 | import sys
  28 | import json
  29 | import subprocess
  30 | import time
  31 | 
  32 | BASE = os.path.dirname(os.path.abspath(__file__))
  33 | sys.path.insert(0, BASE)
  34 | 
  35 | try:
  36 |     import requests
  37 |     HAS_REQUESTS = True
  38 | except ImportError:
  39 |     HAS_REQUESTS = False
  40 | 
  41 | from relay import get_key
  42 | 
  43 | # ── Voice configuration ──────────────────────────────────────────────────────
  44 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST ONLY — Mark at 1.10x speed.
  45 | # Nicole (piTKgcLEGmPE4e6mEKli) and Chris (iP95p4xoKVk53GoZ742B) are BANNED.
  46 | # Both host=1 and host=2 map to Mark.
  47 | 
  48 | _MARK_VOICE = {
  49 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  50 |     "name": "Mark",
  51 |     "model_id": "eleven_turbo_v2_5",
  52 |     "voice_settings": {
  53 |         "stability": 0.55,
  54 |         "similarity_boost": 0.80,
  55 |         "style": 0.15,
  56 |         "use_speaker_boost": True,
  57 |         "speed": 1.10,
  58 |     },
  59 | }
  60 | 
  61 | VOICES = {
  62 |     1: _MARK_VOICE,
  63 |     2: _MARK_VOICE,  # both hosts → Mark (single narrator)
  64 | }
  65 | 
  66 | SILENCE_GAP = 0.3  # seconds between speakers
  67 | MAX_CHUNK_CHARS = 4900
  68 | 
  69 | _KEY_CACHE: dict = {}
  70 | 
  71 | 
  72 | def _get_cached_key(name: str) -> str:
  73 |     if name not in _KEY_CACHE:
  74 |         k = get_key(name)
  75 |         if k:
  76 |             _KEY_CACHE[name] = k.strip()
  77 |     return _KEY_CACHE.get(name, "")
  78 | 
  79 | 
  80 | def ffprobe_duration(path: str) -> float:
  81 |     r = subprocess.run(
  82 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  83 |          "-of", "csv=p=0", path],
  84 |         capture_output=True, text=True,
  85 |     )
  86 |     try:
  87 |         return float(r.stdout.strip())
  88 |     except Exception:
  89 |         return 0.0
  90 | 
  91 | 
  92 | def _generate_silence(output_path: str, duration: float) -> bool:
  93 |     r = subprocess.run(
  94 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  95 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  96 |          "-c:a", "aac", "-b:a", "192k", output_path],
  97 |         capture_output=True, text=True, timeout=30,
  98 |     )
  99 |     return r.returncode == 0 and os.path.exists(output_path)
 100 | 
 101 | 
 102 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
 103 |     r = subprocess.run(
 104 |         ["ffmpeg", "-y", "-i", mp3_path,
 105 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
 106 |         capture_output=True, text=True, timeout=120,
 107 |     )
 108 |     return r.returncode == 0 and os.path.exists(m4a_path)
 109 | 
 110 | 
 111 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
 112 |     if len(text) <= max_chars:
 113 |         return [text]
 114 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
 115 |     sentences = raw.split("\x00")
 116 |     chunks, current = [], ""
 117 |     for sent in sentences:
 118 |         if len(current) + len(sent) + 1 <= max_chars:
 119 |             current = f"{current} {sent}".strip() if current else sent
 120 |         else:
 121 |             if current:
 122 |                 chunks.append(current)
 123 |             current = sent
 124 |     if current:
 125 |         chunks.append(current)
 126 |     return [c for c in chunks if c.strip()]
 127 | 
 128 | 
 129 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 130 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback (quota exhausted)."""
 131 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 132 |     r = subprocess.run([
 133 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 134 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 135 |         output_path,
 136 |     ], capture_output=True, text=True, timeout=15)
 137 |     if r.returncode == 0 and os.path.exists(output_path):
 138 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 139 |         return True
 140 |     return False
 141 | 
 142 | 
 143 | def tts_elevenlabs(text: str, output_path: str, host: int = 1) -> bool:
 144 |     """Generate TTS audio for a single line using the specified host voice.
 145 | 
 146 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 147 |     """
 148 |     if not HAS_REQUESTS:
 149 |         return _tts_generate_silence_fallback(text, output_path)
 150 | 
 151 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 152 |     if not key:
 153 |         return _tts_generate_silence_fallback(text, output_path)
 154 | 
 155 |     voice = VOICES.get(host, VOICES[1])
 156 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 157 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 158 | 
 159 |     chunks = _chunk_text(text)
 160 |     chunk_files = []
 161 | 
 162 |     for ci, chunk in enumerate(chunks):
 163 |         # Extract speed (top-level ElevenLabs param) from voice_settings if present
 164 |         raw_settings = dict(voice["voice_settings"])
 165 |         speed_val = raw_settings.pop("speed", None)
 166 |         body = {
 167 |             "text": chunk,
 168 |             "model_id": voice["model_id"],
 169 |             "voice_settings": raw_settings,
 170 |         }
 171 |         if speed_val is not None:
 172 |             body["speed"] = speed_val
 173 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 174 |         success = False
 175 | 
 176 |         for attempt in range(3):
 177 |             try:
 178 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 179 |                 if r.status_code == 200:
 180 |                     with open(mp3_tmp, "wb") as f:
 181 |                         f.write(r.content)
 182 |                     success = True
 183 |                     break
 184 |                 elif r.status_code == 429:
 185 |                     wait = 2 ** attempt
 186 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 187 |                     time.sleep(wait)
 188 |                 else:
 189 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 190 |                     if attempt < 2:
 191 |                         time.sleep(2 ** attempt)
 192 |             except Exception as e:
 193 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 194 |                 if attempt < 2:
 195 |                     time.sleep(2 ** attempt)
 196 | 
 197 |         if not success:
 198 |             for f in chunk_files:
 199 |                 try:
 200 |                     os.remove(f)
 201 |                 except Exception:
 202 |                     pass
 203 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 204 |             print(f"  [tts] ElevenLabs failed — trying pyttsx3 fallback")
 205 |             try:
 206 |                 import pyttsx3
 207 |                 _engine = pyttsx3.init()
 208 |                 _engine.setProperty("rate", 150)
 209 |                 wav_tmp = output_path + ".pyttsx3.wav"
 210 |                 _engine.save_to_file(chunk, wav_tmp)
 211 |                 _engine.runAndWait()
 212 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 213 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 214 |                     try:
 215 |                         os.remove(wav_tmp)
 216 |                     except Exception:
 217 |                         pass
 218 |                     if ok:
 219 |                         return ok
 220 |             except Exception as pyttsx_err:
 221 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 222 |             return _tts_generate_silence_fallback(text, output_path)
 223 |         chunk_files.append(mp3_tmp)
 224 | 
 225 |     if len(chunk_files) == 1:
 226 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 227 |         try:
 228 |             os.remove(chunk_files[0])
 229 |         except Exception:
 230 |             pass
 231 |         return ok
 232 | 
 233 |     # Multi-chunk concat
 234 |     concat_list = output_path + ".concat.txt"
 235 |     mp3_combined = output_path + ".combined.mp3"
 236 |     with open(concat_list, "w") as f:
 237 |         for p in chunk_files:
 238 |             f.write(f"file '{os.path.abspath(p)}'\n")
 239 |     subprocess.run(
 240 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 241 |          "-c", "copy", mp3_combined],
 242 |         capture_output=True, text=True,
 243 |     )
 244 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 245 |     for f in chunk_files + [concat_list, mp3_combined]:
 246 |         try:
 247 |             if os.path.exists(f):
 248 |                 os.remove(f)
 249 |         except Exception:
 250 |             pass
 251 |     return ok
 252 | 
 253 | 
 254 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 255 |     """Generate audio for the entire dual-host dialogue.
 256 | 
 257 |     Args:
 258 |         dialogue: List of dicts with keys:
 259 |             - host: 1 or 2 (both route to Mark), or "CLIP" (silence placeholder)
 260 |             - text: The line text (or clip description for CLIP)
 261 |             - duration: (CLIP only) silence duration in seconds
 262 |             - source: (CLIP only) source channel name
 263 | 
 264 |     Returns:
 265 |         {
 266 |             "lines": [
 267 |                 {"path": str, "host": int|"CLIP", "duration": float,
 268 |                  "start": float, "text": str},
 269 |                 ...
 270 |             ],
 271 |             "full": str,          # path to concatenated audio
 272 |             "total_duration": float,
 273 |         }
 274 |     """
 275 |     os.makedirs(output_dir, exist_ok=True)
 276 | 
 277 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 278 |     if not key:
 279 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 280 | 
 281 |     silence_path = os.path.join(output_dir, "silence.m4a")
 282 |     _generate_silence(silence_path, SILENCE_GAP)
 283 | 
 284 |     lines = []
 285 |     parts_for_concat = []
 286 |     current_time = 0.0
 287 | 
 288 |     for i, entry in enumerate(dialogue):
 289 |         host = entry.get("host")
 290 |         text = entry.get("text", "")
 291 | 
 292 |         if host == "CLIP":
 293 |             clip_dur = entry.get("duration", 0)
 294 |             lines.append({
 295 |                 "path": None,
 296 |                 "host": "CLIP",
 297 |                 "duration": clip_dur,
 298 |                 "start": current_time,
 299 |                 "source": entry.get("source", ""),
 300 |                 "query": entry.get("query", ""),
 301 |                 "text": text,
 302 |             })
 303 |             continue
 304 | 
 305 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 306 |         voice = VOICES.get(host_num, VOICES[1])
 307 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 308 | 
 309 |         print(f"  [tts] Line {i:02d} ({voice['name']}): {text[:60]}...")
 310 | 
 311 |         if tts_elevenlabs(text, line_path, host_num):
 312 |             dur = ffprobe_duration(line_path)
 313 |             lines.append({
 314 |                 "path": line_path,
 315 |                 "host": host_num,
 316 |                 "duration": dur,
 317 |                 "start": current_time,
 318 |                 "text": text,
 319 |             })
 320 |             parts_for_concat.append(line_path)
 321 |             current_time += dur
 322 | 
 323 |             if i < len(dialogue) - 1:
 324 |                 parts_for_concat.append(silence_path)
 325 |                 current_time += SILENCE_GAP
 326 |         else:
 327 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": host_num,
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "text": text,
 334 |             })
 335 | 
 336 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 337 |     if parts_for_concat:
 338 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 339 |         with open(concat_file, "w") as f:
 340 |             for p in parts_for_concat:
 341 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 342 |         subprocess.run(
 343 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 344 |              "-c", "copy", full_path],
 345 |             capture_output=True, text=True,
 346 |         )
 347 |         if os.path.exists(concat_file):
 348 |             os.remove(concat_file)
 349 | 
 350 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 351 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 352 | 
 353 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 354 | 
 355 |     return {
 356 |         "lines": lines,
 357 |         "full": full_path if os.path.exists(full_path) else None,
 358 |         "total_duration": total_dur,
 359 |     }
 360 | 
 361 | 
 362 | if __name__ == "__main__":
 363 |     from script_writer import generate_script
 364 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 365 |     script = generate_script(style=style)
 366 |     audio_dir = os.path.join(BASE, "output", "audio_test")
 367 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 368 |     print(json.dumps(
 369 |         {k: v for k, v in result.items() if k != "lines"},
 370 |         indent=2,
 371 |     ))
 372 | 
```

### File: video_pipeline_v3/tts_engine.py (420 lines)
```
   1 | #!/usr/bin/env python3
   2 | """TTS Engine V6 — Single-host Mark broadcast voice.
   3 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) at 1.10x speed — PBX approved sole narrator.
   4 | Both host=1 and host=2 route to Mark (no gender swap, no dual-host).
   5 | Generates per-line audio with 0.3s silence gaps."""
   6 | import os, sys, json, subprocess, tempfile, time, struct
   7 | from pathlib import Path
   8 | 
   9 | try:
  10 |     import requests
  11 |     HAS_REQUESTS = True
  12 | except ImportError:
  13 |     HAS_REQUESTS = False
  14 | 
  15 | from relay import get_key
  16 | 
  17 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST — Mark at 1.10x speed.
  18 | # Both host=1 and host=2 map to Mark. Deborah/Brian/Nicole/Chris are all BANNED.
  19 | _MARK_VOICE = {
  20 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  21 |     "name": "Mark",
  22 |     "model_id": "eleven_turbo_v2_5",
  23 |     "speed": 1.10,
  24 |     "voice_settings": {
  25 |         "stability": 0.55,
  26 |         "similarity_boost": 0.80,
  27 |         "style": 0.15,
  28 |         "use_speaker_boost": True,
  29 |     },
  30 | }
  31 | 
  32 | VOICES = {
  33 |     1: _MARK_VOICE,
  34 |     2: _MARK_VOICE,  # single narrator — both hosts are Mark
  35 | }
  36 | 
  37 | # Voice mode overrides for Mark (segment-type tuning)
  38 | VOICE_MODES = {
  39 |     "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18, "speed": 1.10},
  40 |     "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  41 |     "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  42 |     "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18, "speed": 1.10},
  43 |     "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20, "speed": 1.08},
  44 |     "data":            {"stability": 0.60, "similarity_boost": 0.82, "style": 0.12, "speed": 1.10},
  45 | }
  46 | 
  47 | SILENCE_GAP = 0.3  # seconds between speakers
  48 | MAX_CHUNK_CHARS = 4900
  49 | 
  50 | _KEY_CACHE: dict = {}
  51 | 
  52 | 
  53 | def _get_cached_key(name: str) -> str:
  54 |     if name not in _KEY_CACHE:
  55 |         k = get_key(name)
  56 |         if k:
  57 |             _KEY_CACHE[name] = k.strip()
  58 |     return _KEY_CACHE.get(name, "")
  59 | 
  60 | 
  61 | def ffprobe_duration(path: str) -> float:
  62 |     r = subprocess.run(
  63 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  64 |          "-of", "csv=p=0", path],
  65 |         capture_output=True, text=True,
  66 |     )
  67 |     try:
  68 |         return float(r.stdout.strip())
  69 |     except Exception:
  70 |         return 0.0
  71 | 
  72 | 
  73 | def _generate_silence(output_path: str, duration: float) -> bool:
  74 |     """Generate a silent audio file."""
  75 |     r = subprocess.run(
  76 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  77 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  78 |          "-c:a", "aac", "-b:a", "192k", output_path],
  79 |         capture_output=True, text=True, timeout=30,
  80 |     )
  81 |     return r.returncode == 0 and os.path.exists(output_path)
  82 | 
  83 | 
  84 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
  85 |     r = subprocess.run(
  86 |         ["ffmpeg", "-y", "-i", mp3_path,
  87 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
  88 |         capture_output=True, text=True, timeout=120,
  89 |     )
  90 |     return r.returncode == 0 and os.path.exists(m4a_path)
  91 | 
  92 | 
  93 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
  94 |     if len(text) <= max_chars:
  95 |         return [text]
  96 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
  97 |     sentences = raw.split("\x00")
  98 |     chunks, current = [], ""
  99 |     for sent in sentences:
 100 |         if len(current) + len(sent) + 1 <= max_chars:
 101 |             current = f"{current} {sent}".strip() if current else sent
 102 |         else:
 103 |             if current:
 104 |                 chunks.append(current)
 105 |             current = sent
 106 |     if current:
 107 |         chunks.append(current)
 108 |     return [c for c in chunks if c.strip()]
 109 | 
 110 | 
 111 | TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
 112 | 
 113 | 
 114 | def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
 115 |     """SHA256 hash of text+voice+segment_type → stable cache key."""
 116 |     import hashlib
 117 |     payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
 118 |     return hashlib.sha256(payload).hexdigest()[:16]
 119 | 
 120 | 
 121 | def _tts_cache_get(cache_key: str, output_path: str) -> bool:
 122 |     """Check TTS cache and copy to output_path if hit. Returns True on hit."""
 123 |     import shutil
 124 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 125 |     if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000:
 126 |         shutil.copy2(cache_file, output_path)
 127 |         return True
 128 |     return False
 129 | 
 130 | 
 131 | def _tts_cache_put(cache_key: str, audio_path: str) -> None:
 132 |     """Save audio to TTS cache for future runs."""
 133 |     import shutil
 134 |     os.makedirs(TTS_CACHE_DIR, exist_ok=True)
 135 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 136 |     if not os.path.exists(cache_file):
 137 |         shutil.copy2(audio_path, cache_file)
 138 | 
 139 | 
 140 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 141 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback when ElevenLabs quota is exhausted.
 142 | 
 143 |     Estimates duration from text length (~12.5 chars/sec speech rate).
 144 |     Called when both ElevenLabs AND pyttsx3 fail.
 145 |     """
 146 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 147 |     r = subprocess.run([
 148 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 149 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 150 |         output_path,
 151 |     ], capture_output=True, text=True, timeout=15)
 152 |     if r.returncode == 0 and os.path.exists(output_path):
 153 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 154 |         return True
 155 |     return False
 156 | 
 157 | 
 158 | def tts_elevenlabs(text: str, output_path: str, host: int = 1,
 159 |                    segment_type: str = "") -> bool:
 160 |     """Generate TTS for a single line using the specified host voice.
 161 | 
 162 |     Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
 163 |     copies cached audio — no ElevenLabs API call. On miss, generates and caches.
 164 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 165 |     """
 166 |     if not HAS_REQUESTS:
 167 |         # No requests lib — try pyttsx3 or silence
 168 |         return _tts_generate_silence_fallback(text, output_path)
 169 | 
 170 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 171 |     if not key:
 172 |         return _tts_generate_silence_fallback(text, output_path)
 173 | 
 174 |     voice = VOICES.get(host, VOICES[1])
 175 |     # Check TTS cache first — avoid API call if same text+voice was generated before
 176 |     cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
 177 |     if _tts_cache_get(cache_key, output_path):
 178 |         print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
 179 |         return True
 180 | 
 181 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 182 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 183 | 
 184 |     # Apply hybrid voice mode for Mark based on segment type
 185 |     voice_settings = dict(voice["voice_settings"])
 186 |     if host == 1 and segment_type in VOICE_MODES:
 187 |         mode = VOICE_MODES[segment_type]
 188 |         for k, v in mode.items():
 189 |             if k != "speed":
 190 |                 voice_settings[k] = v
 191 | 
 192 |     chunks = _chunk_text(text)
 193 |     chunk_files = []
 194 | 
 195 |     for ci, chunk in enumerate(chunks):
 196 |         body = {
 197 |             "text": chunk,
 198 |             "model_id": voice["model_id"],
 199 |             "voice_settings": voice_settings,
 200 |         }
 201 |         # Add speed parameter — use mode-specific speed for Host 1
 202 |         speed = voice.get("speed", 1.0)
 203 |         if host == 1 and segment_type in VOICE_MODES:
 204 |             speed = VOICE_MODES[segment_type].get("speed", speed)
 205 |         if speed != 1.0:
 206 |             body["speed"] = speed
 207 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 208 |         success = False
 209 | 
 210 |         for attempt in range(3):
 211 |             try:
 212 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 213 |                 if r.status_code == 200:
 214 |                     with open(mp3_tmp, "wb") as f:
 215 |                         f.write(r.content)
 216 |                     success = True
 217 |                     break
 218 |                 elif r.status_code == 429:
 219 |                     wait = 2 ** attempt
 220 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 221 |                     time.sleep(wait)
 222 |                 else:
 223 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 224 |                     if attempt < 2:
 225 |                         time.sleep(2 ** attempt)
 226 |             except Exception as e:
 227 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 228 |                 if attempt < 2:
 229 |                     time.sleep(2 ** attempt)
 230 | 
 231 |         if not success:
 232 |             for f in chunk_files:
 233 |                 try:
 234 |                     os.remove(f)
 235 |                 except Exception:
 236 |                     pass
 237 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 238 |             print(f"  [tts] ElevenLabs failed for chunk {ci} — trying pyttsx3 fallback")
 239 |             try:
 240 |                 import pyttsx3
 241 |                 _engine = pyttsx3.init()
 242 |                 _engine.setProperty("rate", 150)
 243 |                 wav_tmp = output_path + f".pyttsx3.wav"
 244 |                 _engine.save_to_file(chunk, wav_tmp)
 245 |                 _engine.runAndWait()
 246 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 247 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 248 |                     try:
 249 |                         os.remove(wav_tmp)
 250 |                     except Exception:
 251 |                         pass
 252 |                     if ok:
 253 |                         print(f"  [tts] pyttsx3 fallback SUCCESS for chunk {ci}")
 254 |                         return ok
 255 |             except Exception as pyttsx_err:
 256 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 257 |             # Final fallback: generate silence so the segment still renders
 258 |             return _tts_generate_silence_fallback(text, output_path)
 259 |         chunk_files.append(mp3_tmp)
 260 | 
 261 |     # Single chunk
 262 |     if len(chunk_files) == 1:
 263 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 264 |         try:
 265 |             os.remove(chunk_files[0])
 266 |         except Exception:
 267 |             pass
 268 |         if ok and os.path.exists(output_path):
 269 |             _tts_cache_put(cache_key, output_path)
 270 |         return ok
 271 | 
 272 |     # Multi-chunk concat
 273 |     concat_list = output_path + ".concat.txt"
 274 |     mp3_combined = output_path + ".combined.mp3"
 275 |     with open(concat_list, "w") as f:
 276 |         for p in chunk_files:
 277 |             f.write(f"file '{os.path.abspath(p)}'\n")
 278 |     subprocess.run(
 279 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 280 |          "-c", "copy", mp3_combined],
 281 |         capture_output=True, text=True,
 282 |     )
 283 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 284 |     for f in chunk_files + [concat_list, mp3_combined]:
 285 |         try:
 286 |             if os.path.exists(f):
 287 |                 os.remove(f)
 288 |         except Exception:
 289 |             pass
 290 |     if ok and os.path.exists(output_path):
 291 |         _tts_cache_put(cache_key, output_path)
 292 |     return ok
 293 | 
 294 | 
 295 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 296 |     """Generate audio for the entire dual-host dialogue.
 297 | 
 298 |     Args:
 299 |         dialogue: List of {host: 1|2|"CLIP", text: "..."}
 300 |         output_dir: Directory for audio files
 301 | 
 302 |     Returns:
 303 |         {
 304 |             "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
 305 |             "full": str,  # path to concatenated full audio
 306 |             "total_duration": float,
 307 |         }
 308 |     """
 309 |     os.makedirs(output_dir, exist_ok=True)
 310 | 
 311 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 312 |     if not key:
 313 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 314 | 
 315 |     silence_path = os.path.join(output_dir, "silence.m4a")
 316 |     _generate_silence(silence_path, SILENCE_GAP)
 317 | 
 318 |     lines = []
 319 |     parts_for_concat = []
 320 |     current_time = 0.0
 321 | 
 322 |     for i, entry in enumerate(dialogue):
 323 |         host = entry.get("host")
 324 |         text = entry.get("text", "")
 325 | 
 326 |         # Skip CLIP markers — they don't have audio
 327 |         if host == "CLIP":
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": "CLIP",
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "source": entry.get("source", ""),
 334 |                 "query": entry.get("query", ""),
 335 |                 "text": text,
 336 |             })
 337 |             continue
 338 | 
 339 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 340 |         voice = VOICES.get(host_num, VOICES[1])
 341 |         segment_type = entry.get("type", "")
 342 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 343 | 
 344 |         mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
 345 |         print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")
 346 | 
 347 |         if tts_elevenlabs(text, line_path, host_num, segment_type=segment_type):
 348 |             dur = ffprobe_duration(line_path)
 349 |             lines.append({
 350 |                 "path": line_path,
 351 |                 "host": host_num,
 352 |                 "duration": dur,
 353 |                 "start": current_time,
 354 |                 "text": text,
 355 |             })
 356 |             parts_for_concat.append(line_path)
 357 |             current_time += dur
 358 | 
 359 |             # Add silence gap between speakers (not after last line)
 360 |             if i < len(dialogue) - 1:
 361 |                 parts_for_concat.append(silence_path)
 362 |                 current_time += SILENCE_GAP
 363 |         else:
 364 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 365 |             lines.append({
 366 |                 "path": None,
 367 |                 "host": host_num,
 368 |                 "duration": 0.0,
 369 |                 "start": current_time,
 370 |                 "text": text,
 371 |             })
 372 | 
 373 |     # Concatenate all lines into full audio
 374 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 375 |     if parts_for_concat:
 376 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 377 |         with open(concat_file, "w") as f:
 378 |             for p in parts_for_concat:
 379 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 380 |         subprocess.run(
 381 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 382 |              "-c", "copy", full_path],
 383 |             capture_output=True, text=True,
 384 |         )
 385 |         if os.path.exists(concat_file):
 386 |             os.remove(concat_file)
 387 | 
 388 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 389 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 390 | 
 391 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 392 | 
 393 |     return {
 394 |         "lines": lines,
 395 |         "full": full_path if os.path.exists(full_path) else None,
 396 |         "total_duration": total_dur,
 397 |     }
 398 | 
 399 | 
 400 | # Legacy compatibility — V3 pipeline used generate_all_audio
 401 | def generate_all_audio(script: dict, output_dir: str) -> dict:
 402 |     """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
 403 |     if "dialogue" in script:
 404 |         return generate_dialogue_audio(script["dialogue"], output_dir)
 405 |     # V3 fallback
 406 |     raise RuntimeError("V4 pipeline requires dialogue-format script")
 407 | 
 408 | 
 409 | if __name__ == "__main__":
 410 |     from script_writer import generate_script
 411 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 412 |     script = generate_script(style=style)
 413 |     base = os.path.dirname(os.path.abspath(__file__))
 414 |     audio_dir = os.path.join(base, "output", "audio_test")
 415 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 416 |     print(json.dumps(
 417 |         {k: v for k, v in result.items() if k != "lines"},
 418 |         indent=2,
 419 |     ))
 420 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
