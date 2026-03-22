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
- Checks `is_key_valid()` (`198`)
- Sliding 1-hour window via `ApiRequestLog` (`106-123`)
- Burst limit via last 60 seconds (`125-135`)
- Logs successful requests (`235-238`)
- Adds rate limit headers (`246-249`)

**Major correctness issues**
- **Demo key is hardcoded and sequential/guessable**:
  - `routes_premium_api.py:46`
  - `api_key_service.py:262`
  - `STRIPE_SETUP.md:118`
  This violates LAW 2 and LAW 4’s “demo key” intent should still not undermine security.
- **Rate limit is not atomic**. Two concurrent requests can both pass `check_rate_limit()` before either logs the request (`205-238`). Under load, one key can exceed limits significantly.
- **429 responses are not logged**. LAW 2 says track in `api_subscribers table`, and generally usage enforcement should log denied attempts too. This code only logs after successful handler execution (`233-238`), not on rate-limit rejection.
- **401/403 responses are not logged** either.
- `requests_this_hour`, `requests_today`, `rate_window_start` fields in `ApiSubscriber` are effectively dead; only `requests_total` is updated (`159-161`). Dashboard displays `requests_today` (`api_dashboard.html:160-163`) but it will remain stale/zero.
- `require_api_key` assumes handler returns either `(resp, code)` or `resp`; if a handler returns `(resp, code, headers)` this breaks. Not currently used, but fragile.

#### 7. API endpoints
Routes in `core/routes_premium_api.py:283-453`.

What works:
- Topics, entities, sentiment, breaking, signal, status, docs all return JSON.

**Issues**
- `_json_meta()` uses `TIER_LIMITS` rather than subscriber’s actual `rate_limit_per_hour` (`103-122`). If subscriber record differs from tier default, meta is wrong.
- `_get_topics_data()` and `_get_entities_data()` query recent articles without indexes on `Article.published` or `Article.created_at` shown in this diff. Given the law “Every DB query on a sort/filter column MUST have an index,” this is likely non-compliant.
- `_get_entities_data()` uses naive substring matching; “sec” can match unrelated text.
- `_get_breaking_data()` uses article `created_at` as publication time, not `published_at`.
- `/api/v2/terminal/status` exposes subscriber email and metadata to anyone with the key, which is acceptable, but dashboard auth model is weak elsewhere.

#### 8. SSE stream
Route in `core/routes_premium_api.py:340-423`.

What works:
- Returns `text/event-stream`
- Sends connected, heartbeat, breaking, sentiment events

**Major production issues**
- Infinite loop with `time.sleep(15)` per connection (`361-362`) in plain Flask workers will not scale anywhere near “~1000 concurrent users”. This will tie up worker threads/processes.
- It queries DB every 15s per connection (`367-373`, `395-396`). At scale this is expensive.
- No disconnect detection beyond `GeneratorExit`; many WSGI servers buffer/handle this poorly.
- No `retry:` SSE directive.
- No per-channel entitlement beyond generic `stream`.
- No request logging for stream duration/termination; only one request log entry after route returns, which for long-lived streams may never happen until disconnect.

#### 9. Dashboard
Routes in `core/routes_premium_api.py:631-766`.

What works:
- Renders unauthenticated state if no key
- Allows key rotation, billing portal, webhook config

**Major security issue**
- `/api/dashboard?key=pp_cmd_...` is supported (`634-638`, `654-659`, `api_dashboard.html:430`). This leaks API keys into browser history, logs, analytics, referrers, screenshots, and server access logs. Very poor practice for secret-bearing credentials.

**Key rotation correctness bug**
- Comment says “1hr grace period” (`664`, `680`) but implementation immediately replaces the key and invalidates the old one (`679-689`). No grace period exists. This directly contradicts the design in `PHASE0_ADDENDUM.md:28-29`.

**Webhook config**
- Stores `webhook_secret` in plaintext (`models.py:970`, `routes_premium_api.py:752-760`).
- Returns full webhook secret in API response (`756-760`), which is okay only at creation time, but there’s no rotation flow.

---

## SECTION 2: LAW COMPLIANCE

### LAW 1: Stripe keys come from .env — never hardcode
**Status: PARTIAL**

Compliant:
- `STRIPE_SECRET_KEY` read from env in subscribe route (`routes_premium_api.py:473`)
- `STRIPE_COMMANDER_PRICE_ID` read from env (`480`)
- `STRIPE_WEBHOOK_SECRET` read from env (`557`)
- Setup doc exists with steps (`STRIPE_SETUP.md:6-84`)

Violations / partials:
- `core/app.py:5` loads `.env` from `core/.env`, while setup doc says add to `~/protocol_pulse/.env` (`STRIPE_SETUP.md:41-48`). If deployment actually places `.env` at project root, app won’t load it.
- `core/services/stripe_service.py:12-20` also references unrelated `STRIPE_OPERATOR_PRICE_ID` and `STRIPE_SOVEREIGN_PRICE_ID`; not a violation by itself, but unnecessary for this feature.
- Setup doc event list diverges from LAW 3 required events (`STRIPE_SETUP.md:32-35`).

### LAW 2: API keys are UUID4 — never sequential, never guessable
**Status: VIOLATION**

Compliant:
- Normal generated keys use UUID4 (`api_key_service.py:77-82`)

Violations:
- Demo key is hardcoded and trivially guessable:
  - `routes_premium_api.py:46`
  - `api_key_service.py:262`
  - `STRIPE_SETUP.md:118`
- LAW says “Rate limit: 1000 requests/hour per key. Track in api_subscribers table.”
  - Tracking is mostly in `api_request_log`, not `api_subscribers`; only `requests_total` is updated (`api_key_service.py:159-161`), while `requests_this_hour` / `requests_today` are not maintained.
- Addendum says Commander gets 1200/hr (`PHASE0_ADDENDUM.md:16`), but law says 1000/hr. Code uses 1000/hr (`api_key_service.py:29`, `stripe_service.py:171`). The doc/spec package is internally inconsistent, but code should follow the law.

### LAW 3: Webhook validation is non-negotiable
**Status: VIOLATION**

Required: always use `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`, return 400 immediately if validation fails, log attempt, handle `payment_intent.succeeded`, `customer.subscription.deleted`, `invoice.payment_failed`.

Violations:
- If secret missing, webhook is accepted without validation (`routes_premium_api.py:559-565`)
- `payment_intent.succeeded` is not handled (`571-625`)
- Setup doc tells PBX to configure `checkout.session.completed` and `customer.subscription.updated`, but omits `payment_intent.succeeded` (`STRIPE_SETUP.md:32-35`)
- Validation helper does use `stripe.Webhook.construct_event` correctly (`stripe_service.py:224-235`), but route does not enforce it unconditionally.

### LAW 4: API Playground is sandboxed — uses a demo key
**Status: PARTIAL**

Compliant:
- Playground uses demo key (`routes_premium_api.py:771-776`, `api_playground.html:271-273`, `328-343`)
- Playground hits actual endpoints (`api_playground.html:369-403`)
- Demo key rate limit is 20/hr in tier config (`api_key_service.py:28`, `274`)

Violations / partials:
- Demo key is not safely provisioned; it is a fixed hardcoded secret (`api_key_service.py:262`)
- “Read-only demo api_key (tier='demo') that returns sample data” — current implementation hits real endpoints and returns real production data from articles/sentiment, not clearly sandboxed/sample-safe data (`routes_premium_api.py:283-337`). This is only partially compliant with “safe data.”

---

## SECTION 3: SECURITY

### High-risk findings

1. **Unsigned Stripe webhooks accepted when secret missing**
- `core/routes_premium_api.py:559-565`
- This allows anyone to POST forged subscription events and provision/cancel subscribers.

2. **API keys accepted via query string**
- `core/routes_premium_api.py:634-638`
- `core/templates/api_dashboard.html:430`
- Secrets in URLs leak through logs, browser history, referrers, screenshots, analytics.

3. **Hardcoded demo API key**
- `routes_premium_api.py:46`
- `api_key_service.py:262`
- `STRIPE_SETUP.md:118`
- Guessable credential in source control.

4. **Plaintext webhook signing secrets stored in DB**
- `models.py:970`
- `routes_premium_api.py:752-760`
- If DB is leaked, all downstream subscriber webhooks can be forged.

5. **No CSRF/origin protection on dashboard mutation endpoints**
- `/api/dashboard/rotate-key` (`662-694`)
- `/api/dashboard/billing-portal` (`696-728`)
- `/api/dashboard/webhook` (`730-766`)
- They rely only on `X-API-Key`, which is not automatically sent by browsers, so CSRF risk is reduced, but if key is exposed in frontend JS/global scope or copied into malicious scripts, there’s no secondary protection.

### Other security observations

- No SQL injection found in reviewed backend code; SQLAlchemy ORM is used consistently.
- No obvious auth bypass on API endpoints protected by `@require_api_key`.
- However, dashboard is effectively “whoever has the key owns the account,” which is expected for API-key auth, but then exposing key in URL is especially dangerous.
- `app.secret_key` has insecure fallback (`core/app.py:38`). If env missing in production, sessions are weak.
- Logging level is DEBUG globally (`core/app.py:24`) which may expose sensitive operational details in production.
- External CDN JS/CSS in playground (`api_playground.html:4`, `326`) adds supply-chain risk and may violate stricter CSP expectations.

---

## SECTION 4: FRONTEND QUALITY

### Good
- Visual styling is coherent and premium-looking in the new API pages.
- Mobile responsiveness exists at a basic level in dashboard/playground/premium sections.
- Success page is polished.

### Problems

1. **Canvas usage violates stack rule**
- `PHASE0_ADDENDUM.md:40`
- `api_dashboard.html:88`, `210`, `385-424`
- Stack says “NO Canvas.” The dashboard sparkline uses `<canvas>`.

2. **Playground is not fully spec-complete**
- It omits `entities` endpoint from selectable demo endpoints (`api_playground.html:261-267`, `330-336`) even though docs advertise it.
- No empty-state messaging beyond initial placeholder.
- No explicit rate-limit warning UI when 429 occurs beyond raw JSON.

3. **Prism integration is likely incorrect**
- `api_playground.html:288` uses a `<div>` for code snippet, then calls `Prism.highlightElement(el)` (`350-355`).
- Prism usually expects `<pre><code class="language-...">`.
- Response output is a `<pre>` and class is set to `language-json` (`394`), which is closer, but the code snippet block likely won’t highlight correctly.

4. **Dashboard JS uses implicit global `event`**
- `api_dashboard.html:300-312`
- `toggleKey()` references `event.target` without receiving `event`. Works in some browsers, fails in stricter contexts.

5. **Dashboard displays wrong metric**
- “Requests Today” uses `subscriber.requests_today` (`160-163`), but backend never updates it. UI will lie.

6. **Product messaging inconsistency**
- Premium page says card or Bitcoin (`317`, `483-491`) but API flow is Stripe card only.
- FAQ says Bitcoin invoice after checkout (`448-449`) which is unrelated/misleading for this feature.

7. **World-class quality?**
- Better than a raw prototype visually.
- But still feels rushed due to inconsistent copy, misleading payment claims, and a few JS/data mismatches.

---

## SECTION 5: BACKEND QUALITY

### DB operations
Mixed quality.

Good:
- Many writes use try/except + rollback:
  - `stripe_service.py:146-189`
  - `stripe_service.py:199-221`
  - `routes_premium_api.py:593-606`, `611-620`, `690-693`, `762-765`

Weak:
- `core/app.py:148` uses `db.create_all()` at app startup in production. This is not migration-safe in the way the comment claims. It does not reliably add/alter columns; it only creates missing tables.
- Some writes commit without surrounding rollback in same scope:
  - `routes_premium_api.py:682`
  - `routes_premium_api.py:754`
  These are inside try/except, so acceptable, but not ideal if multiple side effects are added later.

### External API calls
- Resend call has timeout, no retry (`routes_premium_api.py:58-92`)
- Stripe calls have no timeout/retry wrappers (`487-501`, `522-525`, `720-723`)
- Webhook delivery has timeout + retry (`795-811`) — good
- SSE has no backpressure strategy — poor

### Cron/background behavior
- Webhook delivery uses ad hoc threads (`845-846`)
- No durable queue, no persistence of attempts, no delivery log table despite addendum claiming “Log all delivery attempts” (`PHASE0_ADDENDUM.md:48`)
- Threads in Gunicorn/multi-worker environments are fragile and can be lost on restart

### Memory / resource concerns
- SSE long-lived generators per connection are the biggest concern (`346-423`)
- Repeated DB polling per stream connection is expensive
- `get_hourly_usage_sparkline()` does 24 separate count queries (`304-312`) — inefficient but acceptable for low volume dashboard use; not ideal

### Logging
Good:
- Many errors are logged with context

Weak:
- Some logs omit identifiers:
  - `billing_portal()` swallows exception variable entirely (`707-708`)
- Invalid API key attempts are not logged
- Rate-limit denials are not logged
- Webhook validation failures are logged, but route still allows bypass if secret missing

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

Material gaps only:

1. **No durable eventing architecture**
   - Bloomberg/Coinbase-grade systems would not implement subscriber webhooks and real-time streams with ad hoc Flask threads and per-connection polling loops. They’d use a queue/pub-sub layer and fan-out workers.

2. **No auditability for billing and entitlements**
   - There is no billing event ledger, no webhook event id deduplication, no delivery log table, no entitlement history. Professionals need traceability.

3. **Weak API key lifecycle**
   - No hashed-at-rest API keys, no last-4 display model, no grace-period rotation implementation, no scoped enforcement beyond a JSON blob, no key creation/revocation history.

4. **Playground is not truly sandboxed**
   - A professional product would serve deterministic sample/demo datasets and clearly label them, while still offering “try live” separately.

5. **No operational scaling path for SSE**
   - For a premium intelligence terminal, real-time delivery is core. Current implementation is not credible for 1000 concurrent users.

What is already good:
- The API surface is clean and understandable.
- The UI direction is strong enough to sell the feature.
- The use of entitlements JSON is a reasonable extensibility choice.

---

## SECTION 7: SCORES (0-100 each)

- Backend logic:    61/100
- Frontend/UI:      72/100
- Error handling:   63/100
- Security:         38/100
- Performance:      46/100
- Law compliance:   42/100
- World-class gap:  40/100
- OVERALL:          52/100

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Enforce Stripe webhook signature validation unconditionally; reject if secret missing | core/routes_premium_api.py:557-569 | currently anyone can forge subscription/cancellation events and mutate paid access

P0 CRITICAL | Remove API key auth via query string from dashboard | core/routes_premium_api.py:634-638, core/templates/api_dashboard.html:430 | API keys will leak into logs, browser history, referrers, and screenshots

P0 CRITICAL | Replace hardcoded demo key with generated non-guessable key and store/retrieve it safely | core/routes_premium_api.py:46, core/services/api_key_service.py:262, STRIPE_SETUP.md:118 | violates LAW 2 and creates a permanent known credential in source control

P0 CRITICAL | Rework SSE implementation off blocking Flask worker loops | core/routes_premium_api.py:346-423 | 1000 concurrent users will exhaust workers and hammer the DB

P0 CRITICAL | Implement atomic rate limiting or transactional reservation for request counts | core/services/api_key_service.py:205-238 | concurrent requests can exceed paid limits and make enforcement unreliable

P1 HIGH     | Handle required `payment_intent.succeeded` webhook event and align setup doc with law | core/routes_premium_api.py:571-625, STRIPE_SETUP.md:31-35 | current implementation is out of spec and may miss required billing state transitions

P1 HIGH     | Stop claiming 1-hour grace period on key rotation unless actually implemented | core/routes_premium_api.py:664-689, PHASE0_ADDENDUM.md:28-29 | current behavior immediately invalidates old keys and will break customer integrations unexpectedly

P1 HIGH     | Hash API keys and webhook secrets at rest; display only prefixes/full value once | core/models.py:948,970, core/routes_premium_api.py:756-760 | plaintext secrets in DB increase blast radius of any DB compromise

P1 HIGH     | Fix `.env` loading path mismatch with deployment/setup instructions | core/app.py:5, STRIPE_SETUP.md:41-48 | production may fail to load Stripe keys even when PBX follows the setup doc

P1 HIGH     | Add indexes for queried/sorted article fields or verify they already exist in omitted model definitions | core/routes_premium_api.py:128-132,161-165,225-229 | current article queries likely violate indexing law and will degrade under load

P1 HIGH     | Remove misleading Bitcoin/Lightning payment claims from API purchase UI/FAQ unless implemented | core/templates/premium.html:317,448-449,483-491 | users will expect payment methods that do not exist for this flow

P1 HIGH     | Update dashboard metrics to use real computed values instead of stale `requests_today` field | core/templates/api_dashboard.html:160-163, core/services/api_key_service.py:159-161 | dashboard currently shows inaccurate usage data

P2 MEDIUM   | Replace `db.create_all()` startup schema management with real migrations only | core/app.py:147-148 | schema drift and missing columns will surface unpredictably in production

P2 MEDIUM   | Deduplicate welcome email sending between webhook and success-page fallback | core/routes_premium_api.py:534-538,577-584 | customers may receive duplicate emails and side effects are duplicated

P2 MEDIUM   | Persist webhook delivery attempts in a DB table with status, latency, and retries | core/routes_premium_api.py:781-846, PHASE0_ADDENDUM.md:45-48 | current delivery system is not auditable or supportable

P2 MEDIUM   | Fix dashboard JS reliance on implicit global `event` | core/templates/api_dashboard.html:300-312 | reveal/hide button can fail in some browsers/contexts

P2 MEDIUM   | Remove Canvas-based sparkline or replace with CSS/SVG | PHASE0_ADDENDUM.md:40, core/templates/api_dashboard.html:88,210,385-424 | violates stated frontend stack constraint

P2 MEDIUM   | Make playground truly sandboxed with sample/demo-safe data responses | core/routes_premium_api.py:283-337,771-776 | current demo key exposes live production data rather than safe sandbox data

P2 MEDIUM   | Optimize sparkline query to aggregate in SQL instead of 24 count queries | core/services/api_key_service.py:304-312 | unnecessary DB load on dashboard views

P3 LOW      | Improve email validation beyond `@` check | core/routes_premium_api.py:470-471 | reduces junk checkout sessions and support noise

P3 LOW      | Add idempotency key to Stripe Checkout session creation | core/routes_premium_api.py:489-501 | avoids duplicate sessions from retries/double-clicks

P3 LOW      | Fix Prism markup/classes for code snippet highlighting | core/templates/api_playground.html:288,350-355 | code samples may not syntax-highlight correctly

P3 LOW      | Populate `stripe_price_id` and `current_period_end` on subscriber records | core/models.py:952,975, core/services/stripe_service.py:147-178 | improves billing accuracy and dashboard usefulness

---

## SECTION 9: THE ONE THING

Stop treating secrets casually: enforce signed webhooks only, remove API keys from URLs, and eliminate the hardcoded demo key before anything else.

---

## SECTION 10: FINAL VERDICT

This is **not production-ready** yet. The biggest blockers are the webhook validation bypass, API key leakage via query params, hardcoded demo key, and an SSE design that will not survive the stated concurrency target. Fix those first, then tighten law compliance and data accuracy before merge.