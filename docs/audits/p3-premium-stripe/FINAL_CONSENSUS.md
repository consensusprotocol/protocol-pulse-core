# CONSENSUS REPORT — P3-PREMIUM-STRIPE — CYCLE 2
Generated: 2026-03-09 14:28
Models: grok, gemini, gpt4o

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | 60 | 68 | 70 | **66** |
| Frontend/UI | 85 | 82 | 85 | **84** |
| Error Handling | 65 | 73 | 75 | **71** |
| Security | 30 | 35 | 45 | **37** |
| Performance | 70 | — | 65 | **68** |
| Law Compliance | 40 | — | 70 | **55** |
| World-Class Gap | 55 | — | 60 | **58** |
| **OVERALL** | **58** | **~62*** | **67** | **62** |

*GPT-4o's overall score was truncated; estimated from subsystem scores.*

> **Synthesis note:** Security and Law Compliance scores diverge most sharply between models. Gemini and GPT-4o correctly bottomed these out due to the webhook bypass. Grok's 45 and 70 respectively represent a significant underreaction to a critical-severity finding. The consensus adopts the lower anchors as correct.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Webhook Signature Validation Can Be Bypassed
**Severity: P0 CRITICAL**
- **What it is:** The Stripe webhook handler contains an explicit `if not webhook_secret:` branch that logs a warning and skips signature validation entirely. Any attacker can POST a crafted `checkout.session.completed` payload to grant themselves a free premium API key with zero authentication.
- **File/line:** `core/routes_premium_api.py:559-565`
- **What to change:** Remove the bypass entirely. If `STRIPE_WEBHOOK_SECRET` is not present in the environment, the handler must immediately `abort(500)` with a log message at CRITICAL level: `"STRIPE_WEBHOOK_SECRET not configured — rejecting all webhook requests"`. There is no safe degraded mode for this control.

### U2 — "Requests Today" Dashboard Metric Is Never Populated
**Severity: P1 HIGH**
- **What it is:** `api_dashboard.html:161` renders `subscriber.requests_today`, a model field (`models.py:957`) that is never written by any backend path. The rate-limiting system is hourly, not daily. Every user sees `0` permanently, making the dashboard look broken.
- **File/line:** `core/templates/api_dashboard.html:161`, `core/models.py:957`
- **What to change:** Either (a) replace with a live `COUNT(*)` query over `ApiRequestLog` filtered to `created_at >= UTC midnight today` in the dashboard route, or (b) remove the metric entirely and replace with "Requests This Hour" which is already tracked. Option (a) is preferred for user trust.

### U3 — Welcome Email Can Be Sent Twice
**Severity: P1 HIGH**
- **What it is:** The success-page fallback path (`routes_premium_api.py:538`) and the webhook handler thread (`routes_premium_api.py:579-584`) both invoke the welcome email send independently, with no coordination flag. Under normal Stripe timing (webhook arrives within seconds of success redirect), both paths execute and the user receives two welcome emails.
- **File/line:** `core/routes_premium_api.py:538`, `core/routes_premium_api.py:579-584`
- **What to change:** Add a `welcome_email_sent` boolean column to `ApiSubscriber` (default `False`). Both code paths must check-and-set this flag atomically before sending. The webhook is the authoritative path; the success-page should not send email at all — it should only display the key.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — N+1 Query in Sparkline Generation
**Models:** Gemini + GPT-4o
- **What it is:** `get_hourly_usage_sparkline()` runs a `COUNT(*)` query inside a Python `for` loop 24 times — one per hour of the day. On a dashboard that refreshes frequently with many subscribers, this is a guaranteed performance bottleneck.
- **File/line:** `core/services/api_key_service.py:304-312`
- **What to change:** Replace the loop with a single query: `SELECT strftime('%H', created_at) as hour, COUNT(*) FROM api_request_log WHERE api_key_id = ? AND created_at >= ? GROUP BY hour`. Hydrate the 24-slot array from the result set, defaulting missing hours to 0.

### M2 — Key Rotation Does Not Implement Specified Grace Period
**Models:** Gemini + GPT-4o (Grok agreed when reviewing others' findings)
- **What it is:** `PHASE0_ADDENDUM.md:29` specifies a 1-hour grace period where both old and new keys work after rotation. The implementation at `routes_premium_api.py:681` invalidates the old key immediately.
- **File/line:** `core/routes_premium_api.py:677-689`, `core/models.py`
- **What to change:** Add `previous_api_key` and `previous_key_expires_at` columns to `ApiSubscriber`. On rotate, move current key → previous, set expiry to `now + 1hr`, generate new key. The `is_key_valid()` check must accept either active key if the previous key's expiry has not elapsed.

### M3 — Dead / Incorrect Stripe Service Functions for Wrong Data Model
**Models:** Gemini + GPT-4o
- **What it is:** `stripe_service.py:34-115` contains `handle_checkout_completed` and `handle_subscription_deleted` that operate on the `User` model. The `p3-premium-stripe` flow uses `ApiSubscriber`. These functions are not called by the new webhook handler but their presence is a maintenance landmine — a future developer hooking them up would corrupt subscriber state silently.
- **File/line:** `core/services/stripe_service.py:34-115`
- **What to change:** Delete these functions or move them to a clearly labeled legacy section with a `# DO NOT USE — User model flow, not ApiSubscriber` header and a docstring explaining the distinction. Prefer deletion.

### M4 — No CSRF Protection on Billable Subscribe Endpoint
**Models:** GPT-4o + Grok
- **What it is:** `POST /api/v2/terminal/subscribe` creates a Stripe Checkout session — a billable action — with no CSRF token validation, no `Origin` header check, and no `Referer` enforcement.
- **File/line:** `core/routes_premium_api.py:459-506`
- **What to change:** Add `Origin`/`Referer` validation at minimum. If the app uses Flask-WTF or a session CSRF token, enforce it here. This prevents cross-origin form submission attacks that initiate checkout sessions.

### M5 — Race Condition Between Success Page and Webhook Provisioning
**Models:** GPT-4o + Grok (Gemini implicitly covered via double-email finding)
- **What it is:** `terminal_subscribe_success` (line 509-550) contains a fallback provisioning call that duplicates the webhook handler's `provision_terminal_subscriber` logic. These two paths can interleave, and the email-send-twice bug (U3) is a direct symptom. The success page is not the right place to provision.
- **File/line:** `core/routes_premium_api.py:529-538`
- **What to change:** Remove provisioning logic from the success page. Replace with a polling UX: show a "Your account is being activated…" spinner and poll `GET /api/v2/terminal/status?session_id=X` (max 10s, 500ms intervals). If not provisioned within 10s, show a "Check your email" message. Webhook remains the single source of truth.

### M6 — Stale Subscriber Fields Not Updated on Reactivation or Webhook Events
**Models:** Gemini + GPT-4o
- **What it is:** The provisioning path for existing/reactivated subscribers does not refresh `rate_limit_per_hour`, `stripe_price_id`, or `current_period_end`. If a subscriber's plan changes or they cancel-and-resubscribe, they inherit stale limits and metadata. The dashboard then shows incorrect renewal info.
- **File/line:** `core/services/stripe_service.py:147-176`, `core/routes_premium_api.py:589-603`
- **What to change:** The `customer.subscription.updated` webhook handler and reactivation path must update all subscriber fields: `rate_limit_per_hour` from the price/plan config, `stripe_price_id` from the subscription object, and `current_period_end` from `subscription.current_period_end`.

### M7 — Stripe API Calls Lack Timeout / Idempotency Controls
**Models:** GPT-4o + Grok
- **What it is:** Stripe checkout session creation has no idempotency key, meaning repeated form submissions or network retries create multiple checkout sessions. There is also no explicit request timeout, leaving Flask worker threads potentially hung during Stripe outages.
- **File/line:** `core/routes_premium_api.py:489-501`
- **What to change:** Generate an idempotency key per checkout attempt (e.g., `hashlib.sha256(f"{email}:{session_nonce}".encode()).hexdigest()`). Pass it as `idempotency_key=` to `stripe.checkout.Session.create()`. Set a `timeout=10` seconds at the Stripe SDK client level.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### GPT-4o Unique: N1 — API Key Leaked via Dashboard URL Query Parameter
**Assessment: IMPLEMENT**
- **What it is:** `/api/dashboard?key=pp_cmd_...` is a supported access pattern. The full API key appears in server logs, browser history, referrer headers, and proxy access logs. This is a real secret-exposure vector even if the dashboard itself is low-risk.
- **File/line:** `core/routes_premium_api.py:633-638`, `core/templates/api_dashboard.html:297`
- **What to change:** Remove query-string key authentication for the dashboard. Replace with a short-lived signed token (`itsdangerous.URLSafeTimedSerializer`) generated server-side after the user authenticates via their API key in a form POST. The token goes in a secure, HTTP-only session cookie. The raw API key must never appear in a URL.

### GPT-4o Unique: N4 — `past_due` Status Does Not Restrict API Access
**Assessment: IMPLEMENT**
- **What it is:** `invoice.payment_failed` sets `subscription_status = "past_due"`, but `is_key_valid()` only rejects `status == "canceled"`. A subscriber whose payment fails remains fully active indefinitely unless manually canceled.
- **File/line:** `core/routes_premium_api.py:608-617`, `core/models.py:996-1004`
- **What to change:** Define and document a grace period policy (e.g., 72 hours). After grace, `is_key_valid()` should reject `past_due` keys. Add a `past_due_since` timestamp column to enforce this. At minimum, document the current behavior as an explicit policy decision.

### GPT-4o Unique: N5 — `current_period_end` Never Populated from Webhook Updates
**Assessment: IMPLEMENT** (overlaps M6 but deserves separate call-out)
- **What it is:** The dashboard renders renewal date from `subscriber.current_period_end`, but `customer.subscription.updated` webhook handler never writes this field. Every subscriber sees a blank/stale renewal date.
- **File/line:** `core/routes_premium_api.py:589-603`, `core/templates/api_dashboard.html:178-180`
- **What to change:** In `customer.subscription.updated` handler, extract `event["data"]["object"]["current_period_end"]` and write it to `ApiSubscriber.current_period_end`.

### GPT-4o Unique: N6 — Full API Key Injected into Dashboard Page JS
**Assessment: INVESTIGATE**
- **What it is:** `const FULL_KEY = "{{ api_key }}";` in the dashboard template. This is necessary for copy/rotate UX but combined with query-string auth (N1) it worsens the exposure surface.
- **Assessment:** This is unavoidable for the copy-to-clipboard feature but becomes lower risk once N1 (URL query-string auth) is fixed. Acceptable post-N1 fix. Close N1 first; this becomes a non-issue.

### Grok Unique: Webhook URL Lacks SSRF/Length Validation
**Assessment: IMPLEMENT**
- **What it is:** Webhook URL configuration at `routes_premium_api.py:731-766` only validates `https://` prefix. A subscriber could supply an internal network URL (e.g., `https://169.254.169.254/...`) to probe the infrastructure.
- **File/line:** `core/routes_premium_api.py:731-766`
- **What to change:** Add a URL allowlist check that rejects RFC-1918 address ranges, loopback, link-local, and hostnames resolving to internal IPs. Use a DNS-resolution check at save time. Add a max URL length of 2048 chars.

### Grok Unique: Demo Key Rate Limit Hardcoded in Multiple Locations
**Assessment: IMPLEMENT**
- **What it is:** The demo key rate limit (20 req/hour) appears in at least two separate files, creating a config drift risk.
- **File/line:** `core/services/api_key_service.py:28`, `core/routes_premium_api.py:447`
- **What to change:** Extract to a single `DEMO_KEY_RATE_LIMIT = 20` constant in a central `config.py` or `constants.py`. Both call sites import from there.

### Gemini Unique: `handle_checkout_completed` Called With Wrong Model
**Assessment: IMPLEMENT** (partially covered in M3 — but Gemini's framing as "dangerous dead code" is the right framing; the unique angle is that it could be wired up by accident during future refactors)
- Already covered in M3 above. No additional action beyond M3.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1: Severity of Webhook Bypass on Grok vs. Gemini/GPT-4o
- **Grok** scored Security at 45 and Law Compliance at 70, implying the webhook bypass, while serious, does not fully break the security posture.
- **Gemini and GPT-4o** scored Security at 30/35 and Law Compliance at 40, treating it as a near-total failure.
- **Verdict: Gemini and GPT-4o are correct.** A bypass of webhook signature verification is not a partial failure — it means the entire webhook-driven provisioning system can be exploited with a single unauthenticated HTTP POST. The LAW explicitly calls this non-negotiable. Grok's scores underrepresent the risk. Consensus security score: **37**.

### Conflict 2: Burst Rate Limit Window (Grok flagged as bug; GPT-4o disagreed)
- **Grok** flagged the 60-second sliding burst window as potentially inconsistent across minute boundaries.
- **GPT-4o** explicitly stated: "A rolling 60-second burst window is fine and actually preferable to aligned minute buckets. That's not a correctness bug."
- **Verdict: GPT-4o is correct.** Rolling windows are the correct implementation for burst limiting. Aligned minute buckets create cliff-edge abuse opportunities (burst at :59, burst again at :01). Grok's concern here is a false positive. **Do not change this logic.**

### Conflict 3: Stripe Timeout — Missing Parameter vs. SDK-Level Issue
- **Grok** treated missing timeout as a straightforward `timeout=` parameter fix.
- **GPT-4o** noted the Stripe Python SDK manages HTTP internally and the real issue is idempotency/retry policy.
- **Verdict: GPT-4o's framing is more precise.** The correct fix is idempotency keys (M7) and SDK-level `http_client` timeout configuration, not a per-call parameter. However, both models agree action is needed — the mechanism differs, not the conclusion.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

1. **Stripe Keys from Environment Variables (LAW 1 COMPLIANT):** Consistent use of `os.environ.get()` for all Stripe credentials. No hardcoded secrets. Setup documentation in `STRIPE_SETUP.md` is clear. Do not change this pattern.

2. **UUID4 API Key Generation (LAW 2 COMPLIANT):** `api_key_service.py:81` uses `uuid.uuid4()` with correct prefix formatting. The rate-limiting infrastructure (`api_request_log` table + sliding window) is correctly implemented.

3. **Sliding Window Rate Limiting Logic:** The hourly sliding window in `check_rate_limit` (`api_key_service.py:100-141`) is algorithmically correct and superior to bucket-based alternatives. The burst window is intentionally rolling. Do not change this logic.

4. **API Playground Sandboxing (LAW 4 COMPLIANT):** The playground is correctly provisioned with demo key limits and does not share state with production keys.

5. **Overall Frontend UI Polish:** The premium page and dashboard HTML/CSS are high quality. The checkout flow UX is clean. Minor content issues (misleading metric, spec placement) are addressable without redesign.

6. **Webhook Handler Structure:** The dispatch pattern (event type → handler function) in the webhook route is correctly structured. The fix required (U1) is surgical — the architecture itself is sound.

---

## LAW COMPLIANCE CONSENSUS

| Law | Description | Status | Determination |
|---|---|---|---|
| LAW 1 | Stripe keys from `.env` | ✅ COMPLIANT | All models agree. `os.environ.get()` used consistently. |
| LAW 2 | API keys are UUID4 with rate limiting | ✅ COMPLIANT | All models agree. UUID4 generation and sliding window are correct. |
| LAW 3 | Webhook validation is non-negotiable | ❌ **VIOLATED** | All models ultimately agree. `if not webhook_secret: skip` is an explicit bypass. This is the single most important fix in this codebase. |
| LAW 4 | API Playground is sandboxed | ✅ COMPLIANT | All models agree. Demo key isolation is correct. |

**LAW 3 is violated. This is a ship-blocker.**

---

## SECURITY CONSENSUS

Priority order of security issues by consensus severity:

1. **[CRITICAL] Webhook signature bypass** — Unauthenticated account provisioning. `routes_premium_api.py:559-565`. All 3 models.
2. **[HIGH] API key in URL query string** — Secret leaks to logs, browser history, referrers. `routes_premium_api.py:633-638`. GPT-4o only, but technically sound and clearly correct.
3. **[HIGH] CSRF missing on billable POST** — Cross-origin checkout session creation. `routes_premium_api.py:459-506`. 2 models.
4. **[MEDIUM] Webhook URL SSRF via internal address** — Subscriber-controlled URL with no network-scope validation. `routes_premium_api.py:731-766`. Grok only, but valid.
5. **[MEDIUM] `past_due` subscribers retain full API access** — Indefinite access after payment failure. `models.py:996-1004`. GPT-4o only, but policy gap is real.
6. **[LOW] Full key injected into page JS** — Acceptable once URL leak (item 2) is fixed. `api_dashboard.html:297`.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

1. **Single authoritative provisioning path (webhook-only)** — Gemini + GPT-4o + Grok. World-class Stripe integrations treat the success page as a display-only confirmation. All state changes flow through the verified webhook. The current dual-path design (success page + webhook both provision) is the root cause of U3, M5, and several secondary bugs.

2. **Resilient operational infrastructure** — Gemini + Grok. No retry queues for email, no persistent failure tracking for outbound webhooks, no alerting on critical path failures. A world-class feature has observable failure modes, not silent ones.

3. **Centralized configuration over magic literals** — GPT-4o + Grok. Rate limits, scopes, price IDs, and tier definitions are scattered across multiple files. A world-class system has a single source of truth for plan configuration that the webhook handler, dashboard, and API all read from.

4. **Complete subscriber lifecycle** — Gemini + GPT-4o. Fields like `current_period_end`, `stripe_price_id`, and `rate_limit_per_hour` are not consistently populated across the subscriber lifecycle (initial provision, plan change, reactivation). A world-class subscription product reflects ground truth at every state transition.

5. **Spec-compliant key rotation** — Gemini + GPT-4o. The documented 1-hour grace period for key rotation is not implemented. World-class APIs honor their documented migration windows because developers build deployment pipelines around them.

---

## FINAL ACTION PLAN (sorted by consensus priority)

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Remove webhook signature bypass. If `STRIPE_WEBHOOK_SECRET` is absent, `abort(500)` with CRITICAL log. Never process unsigned payloads. | `core/routes_premium_api.py:559-565` | All 3 | LAW 3 violation. Enables free account creation via forged POST. Ship blocker. |

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Replace 24-query sparkline loop with single `GROUP BY` query. | `core/services/api_key_service.py:304-312` | Gemini + GPT-4o | N+1 performance bug. Degrades with scale. |
| P1-2 | Implement "Requests Today" via live `COUNT(*)` query or remove metric. | `core/templates/api_dashboard.html:161`, `core/models.py:957` | All 3 | Always-zero metric erodes user trust in the product. |
| P1-3 | Add `welcome_email_sent` boolean to `ApiSubscriber`. Check-and-set atomically before any send. Remove email send from success-page path. | `core/routes_premium_api.py:538`, `579-584` | All 3 | Users currently receive two welcome emails under normal Stripe timing. |
| P1-4 | Remove provisioning logic from success page. Replace with polling UX (max 10s) against a lightweight status endpoint. | `core/routes_premium_api.py:529-538` | GPT-4o + Grok (Gemini via implication) | Dual provisioning path is root cause of U3, M5, and brittle race conditions. |
| P1-5 | Remove query-string API key authentication for dashboard. Use short-lived signed session token (itsdangerous) in HTTP-only cookie. | `core/routes_premium_api.py:633-638` | GPT-4o (unique but critical) | API keys in URLs leak to logs, browser history, and referrer headers. |
| P1-6 | Add CSRF/Origin protection to `POST /api/v2/terminal/subscribe`. | `core/routes_premium_api.py:459-506` | GPT-4o + Grok | Billable action exposed to cross-origin form submission. |
| P1-7 | Update `customer.subscription.updated` handler to write `current_period_end`, `stripe_price_id`, `rate_limit_per_hour` on every state change. | `core/routes

---

# WINNER DETERMINATION

## WINNER: GPT-4o

GPT-4o delivered the highest-quality analysis overall by combining the greatest depth of original Cycle 1 findings (CSRF absence, idempotency key omission, weak email validation, race-condition mechanics in the success route, Bitcoin/Lightning UI mismatch) with the most actionable, file-line-specific recommendations that were independently confirmed correct in Cycle 2. While Gemini demonstrated strong structural reasoning and Grok showed breadth, GPT-4o's Cycle 1 output contained the most unique, implementable findings that the other two models had to acknowledge missing — the definitive mark of analytical leadership in a cross-audit format.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by: severity → blast radius → implementation cost (cheapest fixes first within a tier)

---

### P0 — CRITICAL / SHIP BLOCKER (fix before merge)

**1. Webhook Signature Bypass [U1]**
`core/routes_premium_api.py:559-565`
Remove the `if not webhook_secret:` soft-fail branch entirely. Replace with:
```python
if not webhook_secret:
    app.logger.critical("STRIPE_WEBHOOK_SECRET not configured — rejecting all webhook requests")
    abort(500)
```
No degraded mode is acceptable. This is an unauthenticated account-takeover vector.

**2. No CSRF Protection on Billable POST Route**
`core/routes_premium_api.py:459-506`
Add origin-check or Flask-WTF CSRF token validation on `/api/v2/terminal/subscribe`. A forged POST from any authenticated session creates a billable Stripe Checkout. Minimum fix: validate `Origin`/`Referer` header against `SERVER_NAME`; preferred fix: require CSRF token in POST body.

**3. Welcome Email Double-Send Race [U3]**
`core/routes_premium_api.py:538` and `579-584`
Both the success-page fallback provisioning path and the webhook handler send the welcome email independently with no coordination flag. Add a `welcome_email_sent` boolean column to `ApiSubscriber`; gate both send paths on `not subscriber.welcome_email_sent` and set it atomically before sending. Use `SELECT FOR UPDATE` or equivalent to prevent the race.

---

### P1 — HIGH / REQUIRED BEFORE GA

**4. "Requests Today" Metric Never Populated [U2]**
`core/templates/api_dashboard.html:161`, `core/models.py:957`
Either: (a) remove the field from the dashboard and model entirely if the roadmap does not support it, or (b) implement a daily aggregation job that writes to `requests_today` at midnight UTC and increments it on each authenticated request in `check_rate_limit`. Do not display a metric that is permanently zero — it destroys subscriber trust.

**5. Key Rotation Grace Period Specification Mismatch**
`core/routes_premium_api.py:677-689`, `PHASE0_ADDENDUM.md:29`
The spec requires a 1-hour grace period for rotated keys. The implementation invalidates immediately. Add `old_key_expires_at = datetime.utcnow() + timedelta(hours=1)` to `ApiSubscriber`, check it in `validate_api_key`, and purge on next cron. If the spec decision has been reversed, update `PHASE0_ADDENDUM.md` explicitly — do not leave a silent contradiction between implementation and architecture docs.

**6. No Idempotency Key on Stripe Checkout Session Creation**
`core/routes_premium_api.py:487-501`
Repeated clicks or network retries create multiple Checkout sessions for the same user. Pass `idempotency_key=f"checkout-{email}-{int(time.time() // 300)}"` (5-minute window) to the Stripe SDK call. This is standard Stripe hygiene and prevents duplicate billing exposure.

**7. Dead/Incorrect Code in `stripe_service.py`**
`core/services/stripe_service.py:34-115`
`handle_checkout_completed` and `handle_subscription_deleted` operate on the `User` model, not `ApiSubscriber`. They are unreachable by the current webhook router but represent a future-footgun if a developer wires them up during maintenance. Delete both functions or add a module-level `raise NotImplementedError` with a comment explaining the correct `ApiSubscriber` path.

---

### P2 — MEDIUM / REQUIRED BEFORE SCALE

**8. N+1 Query in Sparkline Generation**
`core/services/api_key_service.py:304-311`
`get_hourly_usage_sparkline()` executes 24 separate `COUNT` queries in a loop. Replace with a single query:
```sql
SELECT DATE_TRUNC('hour', created_at) AS hour, COUNT(*)
FROM api_requests
WHERE api_key_id = :id AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY 1 ORDER BY 1
```
Fill zero-count hours in Python. This is a dashboard-load regression waiting to happen at any meaningful subscriber count.

**9. Weak Email Validation**
`core/routes_premium_api.py:470-471`
Current check passes any string containing `@`. Use `email-validator` library (`validate_email(email, check_deliverability=False)`) and return HTTP 400 with a user-facing message on failure. This also gates downstream Stripe customer creation on garbage input.

**10. Missing Subscriber Field Population in Provisioning and Webhook Updates**
`core/routes_premium_api.py` (provisioning path), webhook handler
`stripe_price_id`, `current_period_end`, and `rate_limit_per_hour` are not consistently written during both provisioning and `customer.subscription.updated` webhook handling. Define a single `sync_subscriber_from_stripe(subscriber, stripe_subscription)` helper function called from both paths to guarantee field consistency. Never let these diverge.

**11. No Timeout or Retry Wrapper on Stripe API Calls**
`core/routes_premium_api.py:487-501` and webhook handler
Stripe SDK calls are made bare with no timeout configuration. A Stripe API hang will block the request thread indefinitely. Set `stripe.default_http_client = stripe.HTTPXClient(timeout=10.0)` at app init, and wrap checkout session creation in a `try/except stripe.error.Timeout` with a user-facing 503 response.

---

### P3 — LOW / QUALITY & POLISH

**12. Bitcoin/Lightning Payment Method Claim Is False**
`core/templates/premium.html:483-491`
The UI lists Bitcoin/Lightning as accepted payment methods. This feature only implements Stripe card checkout. Remove or qualify the claim until Lightning is actually implemented. This is a consumer-protection issue on a billing page.

**13. UI/Spec Layout Mismatch**
`core/templates/premium.html:320-369`, `PHASE0_ADDENDUM.md:60-61`
The Terminal API card is implemented as a standalone hero section above the pricing grid rather than an in-grid card between Commander and Sovereign as specified. Not a functional bug, but document the deviation or align the implementation to the spec before stakeholder review.

**14. Burst Rate Limit Window Is Not Minute-Aligned**
`core/services/api_key_service.py:126-134`
The burst check uses a rolling 60-second window from the current timestamp rather than aligning to clock-minute boundaries. This produces inconsistent behavior at minute edges. Align to `floor(now / 60) * 60` or document the rolling-window behavior explicitly so support can explain it to subscribers.