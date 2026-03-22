# CONSENSUS REPORT — V30-TERMINAL-API — CYCLE 2
Generated: 2026-03-09 02:39
Models: Gemini, GPT-4o, Grok

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | 10/100 | 10/100 | 10/100 | **10/100** |
| Error Handling | 15/100 | 18/100 | 20/100 | **18/100** |
| Security | 20/100 | 24/100 | 25/100 | **23/100** |
| Performance | 35/100 | 43/100 | 50/100 | **43/100** |
| Law Compliance | 15/100 | 14/100 | 15/100 | **15/100** |
| **Overall** | **~19/100** | **22/100** | **24/100** | **22/100** |

> **Scoring note:** The 3-model spread is narrow — within 5 points on every subsystem. This is unusually high inter-model agreement and should be read as strong signal. The feature scores in the 10–24 range across every meaningful dimension because the core implementation simply does not exist in the review set.

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

---

### U1 — Core implementation files are entirely absent

**What it is:** The files that constitute the actual feature — `routes_api_terminal.py`, Stripe subscription route(s), Stripe webhook handler(s), and the API key auth middleware — are not present in the submitted code. `app.py` registers a `terminal_bp` blueprint that points to a non-existent file.

**File/Line:** `app.py:263–266` (blueprint import), plus all missing files listed above.

**What to change:** The five Commander endpoints (`/api/v2/terminal/topics`, `/api/v2/terminal/sentiment`, `/api/v2/terminal/signals`, `/api/v2/terminal/alerts`, `/api/v2/terminal/subscribe`), auth middleware, and Stripe integration must be written and submitted before any further review or merge is possible. This is the single largest gap in the feature.

---

### U2 — Silent blueprint failure masks dead routes at startup

**What it is:** Both the `terminal_bp` and `commander_bp` registrations are wrapped in broad `try/except Exception` blocks. If either import fails, the server boots successfully, logs a warning or prints an error, and returns 404s silently. Paying Commander-tier users have no access and no indication anything is wrong. The deployment appears healthy.

**File/Line:** `app.py:263–266` (terminal), `app.py:268–272` (commander)

**What to change:** Remove both `try/except` blocks. Blueprint registration for a monetized feature must be a hard startup failure. The application should not start if its paid routes cannot be loaded. Pattern to replace:

```python
# REMOVE THIS PATTERN:
try:
    from routes_api_terminal import terminal_bp
    app.register_blueprint(terminal_bp)
except Exception as e:
    print(f"Terminal API not loaded: {e}")

# REPLACE WITH:
from routes_api_terminal import terminal_bp
app.register_blueprint(terminal_bp)
```

---

### U3 — Rate limiting is IP-based at 200/day, spec requires API-key-based at 1000/day

**What it is:** The global `flask_limiter` in `app.py` uses `get_remote_address` as the identity key and sets a default limit of `"200 per day"`. The spec requires per-API-key rate limiting at 1000 requests/day for Commander tier. This is wrong on two axes simultaneously: wrong identity (IP vs. key) and wrong quota (200 vs. 1000). Under the current setup, multiple Commander customers behind the same NAT or proxy share a single 200-request budget, while a single customer with multiple IPs gets multiple 200-request allocations. Neither behavior is acceptable for a paid product.

**File/Line:** `app.py:96–97`

**What to change:** Replace the global IP-based limiter with a key-aware limiter. Terminal endpoints must extract the `X-PP-API-Key` header and use the key identity (or its hash) as the rate-limit key. Apply a per-endpoint decorator with the correct 1000/day quota. Exempt or separately configure other app routes so Commander-specific logic does not bleed into general web routes.

---

## MAJORITY FINDINGS
*(2 of 3 models agree — implement unless compelling reason not to)*

---

### M1 — Public cache headers on `/api/` responses (GPT-4o + Gemini)

**What it is:** `app.py:153–157` sets `response.cache_control.public = True` for API responses. For an authenticated, paid API, this instructs shared caches (CDN edge nodes, corporate proxies) to store and serve responses. Rate-limit metadata, usage counts, or any per-key response data could be served to unrelated clients from a shared cache layer.

**File/Line:** `app.py:153–157`

**What to change:** Set `Cache-Control: private, no-store` for all `/api/v2/terminal/*` routes. If the existing after-request hook is global, add a conditional check on the request path before setting the public header, or override caching explicitly in the Terminal API blueprint.

---

### M2 — Fallback hardcoded secret key in production (GPT-4o + Grok)

**What it is:** `app.py:46` sets `app.secret_key` to a hardcoded string `"dev_secret_key_protocol_pulse_2026"` if `SESSION_SECRET` is not present in the environment. In production, if the environment variable is misconfigured or missing, the application silently uses a known, public key. This invalidates all session security.

**File/Line:** `app.py:46`

**What to change:** Detect the environment mode. If running in production (e.g., `FLASK_ENV=production` or `ENV=production`), abort startup with a fatal error if `SESSION_SECRET` is absent. The fallback is only acceptable for local development with an explicit warning printed to stdout.

---

### M3 — `db.create_all()` at runtime conflicts with Alembic (GPT-4o + Gemini)

**What it is:** `app.py:243–247` calls `db.create_all()` inside the application context at startup. Because Alembic is also used for migrations, these two mechanisms can diverge. If `create_all()` runs before a migration, it may create tables in a state that Alembic does not recognize as migrated, preventing future `alembic upgrade head` calls from running correctly.

**File/Line:** `app.py:243–247`

**What to change:** Remove the `db.create_all()` call from startup. All schema management must go through Alembic exclusively. If a "first run" convenience is needed in development, guard it behind a development-only environment flag with a prominent warning.

---

### M4 — Redundant database index on `key_hash` (Gemini + GPT-4o + Grok all noted, but Gemini/GPT-4o were most specific)

**What it is:** The migration creates both a composite index `idx_api_keys_hash_active` on `(key_hash, active)` and a separate single-column index `ix_api_keys_key_hash` on `key_hash`. The composite index satisfies all queries that filter only on `key_hash` (the database uses the leftmost prefix), making the single-column index redundant. It adds write overhead and storage cost with no query benefit.

**File/Line:** `migrations/versions/v30_terminal_api_keys.py:39–40`

**What to change:** Drop `ix_api_keys_key_hash`. Retain only `idx_api_keys_hash_active`. Verify that the unique constraint on `key_hash` is enforced at the column level (which it is, via `unique=True`) so the index removal does not affect uniqueness guarantees.

---

### M5 — `key_prefix` column length may not match key format (GPT-4o + Grok)

**What it is:** The `api_keys` table defines `key_prefix` as `varchar(12)` (`migration:23`). The spec key format is `pp_cmd_{32 random chars}`. The prefix `pp_cmd_` is 7 characters. If the intent is to store the first 12 characters of the full key for display/support purposes (e.g., `pp_cmd_xxxxx`), the length is plausible but not documented. If the intent is to store only the literal prefix `pp_cmd_`, 7 characters suffices. The same field appears in `api_usage_log` at `migration:49`. Without the key generation code, the correct behavior is unverifiable, but the ambiguity is a latent bug risk.

**File/Line:** `migrations/versions/v30_terminal_api_keys.py:23, 49`

**What to change:** Document in a comment exactly what the `key_prefix` field contains (first N chars of full key, or literal prefix string). Ensure the key generation code, the storage length, and the display/lookup logic are consistent. If the field stores the first 12 characters of `pp_cmd_{32chars}`, rename it `key_display_prefix` and add a comment.

---

## UNIQUE INSIGHTS
*(Only 1 model raised this — evaluated individually)*

---

### UI1 — No key deactivation path for subscription cancellations (Gemini only)
**Assessment: IMPLEMENT — P0 severity**

This is a critical business logic gap that Gemini alone explicitly named. The `api_keys` table has an `active` column defaulting to `True`, but there is no Stripe webhook handler for `customer.subscription.deleted` or `customer.subscription.updated` (status → canceled). Without this, users who cancel their Commander subscription retain API access indefinitely. This is both a revenue protection failure and a ToS enforcement failure. Gemini was right to flag it. It must be built alongside the Stripe integration.

---

### UI2 — `api_usage_log` uses `key_prefix` instead of a foreign key (GPT-4o + partially Grok, strongest articulation from GPT-4o)
**Assessment: IMPLEMENT at P1**

The `api_usage_log` table stores `key_prefix` as its link back to `api_keys`, not a proper `api_key_id` foreign key (`migration:47–61`). This denormalization means:
- Joins for billing, abuse detection, or support queries require a string match rather than an integer FK lookup
- If a key is revoked and re-issued with the same prefix (unlikely but possible), usage logs become ambiguous
- Cascade delete or referential integrity cannot be enforced

The correct design adds `api_key_id INTEGER REFERENCES api_keys(id)` to `api_usage_log` and keeps `key_prefix` only as a display/debug convenience column. This is a schema fix that is far cheaper to make now than after data accumulates.

---

### UI3 — Daily quota reset semantics are underspecified and likely race-prone (GPT-4o, sharpened from Grok's hint)
**Assessment: IMPLEMENT at P1**

The schema stores `requests_today` and `last_reset_at` on the `api_keys` row. GPT-4o correctly identified that naïve app-level increment logic (`UPDATE api_keys SET requests_today = requests_today + 1 WHERE key_hash = ?`) is not safe under concurrent requests. Two simultaneous requests can both read `requests_today = 999`, both determine they are under the limit, and both increment — allowing 1001st and 1002nd requests through. Additionally, the reset mechanism (comparing current date to `last_reset_at`) has timezone ambiguity.

The recommended design is one of:
- A single atomic SQL expression: `UPDATE api_keys SET requests_today = requests_today + 1, last_reset_at = CASE WHEN DATE(last_reset_at) < DATE('now') THEN DATE('now') ELSE last_reset_at END WHERE key_hash = ? RETURNING requests_today`
- Or: derive daily usage directly from `api_usage_log` grouped by `DATE(created_at)` and eliminate the mutable counter entirely (more accurate, no race risk, cheaper to maintain)

---

### UI4 — Required env var policy is inconsistent with a paid launch (GPT-4o only)
**Assessment: INVESTIGATE — promote to P1 if Stripe secrets are confirmed as required at launch**

`app.py:72–85` defines "required" env vars but explicitly states startup should "never hard-crash." For a general-purpose web app this philosophy has merit. For a paid API launch, missing `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, or `MAIL_*` config should be fatal in production because those env vars underpin the subscription flow and API key delivery. The policy needs a carve-out: certain vars are advisory-warn-and-continue; payment and delivery vars must be fatal-on-missing.

---

### UI5 — Branch hygiene: unrelated files included in PR (Gemini + GPT-4o, both noted)
**Assessment: IMPLEMENT — P2, process fix**

`media_reforge/static/js/media_unified.js`, `run_..._audit.py` scripts, and `launch_all_features.sh` are unrelated to `v30-terminal-api`. Their presence in this review set inflated the review surface and risks accidentally shipping unreviewed code changes to unrelated systems. The PR must be scoped to only the files that implement this feature. Branch should be rebased or the unrelated files reverted before merge.

---

## CONFLICTS
*(Models gave contradictory assessments — tiebreaker applied)*

---

### C1 — Severity of `db.create_all()` at runtime

**GPT-4o** treated it as high severity. **Grok** called it "partially agree, less critical for this feature specifically." **Gemini** agreed it should be removed.

**Tiebreaker: GPT-4o and Gemini are correct.** The risk is not hypothetical — a team running `db.create_all()` and Alembic simultaneously in a CI environment has a well-documented failure mode where Alembic's `alembic_version` table diverges from the actual schema. For a feature adding new tables, this is especially risky. The `partial agree` framing from Grok underestimates the operational impact. Remove `db.create_all()`.

---

### C2 — Severity of public cache headers

**GPT-4o** called it a real security and privacy risk. **Grok** said "partially agree" with lower severity "without endpoint code." **Gemini** agreed it was a security and correctness flaw.

**Tiebreaker: GPT-4o and Gemini are correct.** You do not need to see the endpoint code to know that setting `Cache-Control: public` on an authenticated API is wrong by design. Rate-limit headers alone (e.g., `X-RateLimit-Remaining`) constitute sensitive per-user information. Grok's "wait and see" framing is overly cautious. Fix it proactively.

---

### C3 — Performance score for migration/indexes

**Grok** scored performance at 50/100, noting indexes are present and positive. **GPT-4o** gave 43/100. **Gemini** gave 35/100, weighted down by the redundant index and usage log schema.

**Tiebreaker: Gemini's lower score is the most defensible.** The redundant index and the foreign-key-less usage log schema are real structural problems, not just style issues. The usage log design will produce slow analytical queries at scale. 35–40/100 is the right range. Grok's 50/100 was too generous given the missing implementation.

---

## VALIDATED STRENGTHS
*(All models confirmed — do NOT change in second pass)*

---

### VS1 — Storing `key_hash` instead of raw API keys

All three models confirmed this is the correct security practice. The raw key is never stored; only a hash is persisted for lookup. This is correct and must not be changed.

**File/Line:** `migrations/versions/v30_terminal_api_keys.py:22`

---

### VS2 — Composite index design on high-frequency lookup columns

The migration creates indexes on `key_hash`, `subscriber_email`, `stripe_customer_id`, `last_used_at`, and `active`. Aside from the redundancy issue addressed in M4, the overall indexing strategy for the `api_keys` table is well-considered for the expected query patterns (auth lookups by hash, support lookups by email, billing lookups by Stripe ID). All models acknowledged this was good practice.

**File/Line:** `migrations/versions/v30_terminal_api_keys.py:39–44`

---

### VS3 — Separation of `api_keys` and `api_usage_log` into distinct tables

The decision to log usage in a separate table rather than accumulating state solely on the `api_keys` row (aside from the counter) is architecturally sound. It preserves a full audit trail and enables per-request analytics. All models treated this as a positive design decision. The foreign key gap (UI2) is a fix to the implementation of this decision, not a rejection of the design.

**File/Line:** `migrations/versions/v30_terminal_api_keys.py:46–61`

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Determination |
|---|---|---|
| **LAW 1:** Commander tier ($49/mo) ships first | **PARTIAL** | Schema supports a `tier` column. No endpoint code exists to enforce Commander-only access. Watcher/Sovereign tiers are not implemented, which is correct. Cannot verify full compliance without implementation. |
| **LAW 2:** API auth via API keys (not JWT, not OAuth) | **VIOLATION** | Rate limiting is IP-based at 200/day. No `X-PP-API-Key` middleware is present in the reviewed code. The schema supports key-based auth, but the enforcement layer does not exist. |
| **LAW 3:** Five Commander endpoints must exist | **VIOLATION** | Zero of five endpoints are present in the reviewed code. `routes_api_terminal.py` is missing entirely. |
| **LAW 4:** Stripe subscription flow | **VIOLATION** | No Stripe route, session creation, or webhook handler is present in the reviewed code. |
| **LAW 5:** Email delivery of API key on successful payment | **VIOLATION** | No webhook handler exists to trigger key generation and email delivery. |

**Overall Law Compliance: 4 of 5 laws are in active violation. 1 is partially met at schema level only. This feature does not legally satisfy the specification as reviewed.**

---

## SECURITY CONSENSUS

Priority-ordered security issues confirmed by 2+ models:

| Priority | Issue | Models | Severity |
|---|---|---|---|
| S1 | Hardcoded fallback secret key in production (`app.py:46`) | GPT-4o, Grok | Critical |
| S2 | IP-based rate limiting instead of API-key-based (`app.py:96–97`) | All 3 | Critical — enables quota bypass via IP rotation |
| S3 | Silent blueprint failure creates undetected service outage (`app.py:263–272`) | All 3 | Critical — operational |
| S4 | Public cache headers on authenticated API responses (`app.py:153–157`) | Gemini, GPT-4o | High — cache poisoning / data leakage |
| S5 | No key deactivation on subscription cancellation | Gemini | High — revenue and access control |
| S6 | Race condition on `requests_today` counter | GPT-4o, Grok (indirect) | Medium — quota enforcement bypass |
| S7 | No email format validation on `subscriber_email` | Grok | Low — silent delivery failure |

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned as missing from a truly excellent product)*

---

**Gap 1 — No deactivation/revocation lifecycle for API keys (Gemini + implied by GPT-4o's Stripe webhook discussion)**
A world-class API product has a complete key lifecycle: creation on payment, rotation on request, revocation on cancellation, expiry on non-payment. The current schema and implementation have only creation. There is no rotation endpoint, no revocation endpoint, and no webhook to drive state changes. This is not a minor gap — it is the difference between an API product and a demo.

**Gap 2 — No idempotent usage counting under concurrency (GPT-4o + Grok)**
A world-class rate limiter uses atomic operations or a dedicated rate-limiting layer (Redis with INCR + EXPIRE, or a purpose-built library). The current mutable counter design on the `api_keys` row will fail under realistic concurrent load. At Commander scale, this produces both security vulnerabilities (over-limit access) and billing inaccuracies.

**Gap 3 — Usage log lacks referential integrity (GPT-4o + Gemini noted denormalization)**
A world-class billing and analytics schema uses proper foreign keys. The `key_prefix` string join in `api_usage_log` is adequate for a prototype but will create operational pain at scale — slow billing queries, ambiguous data after key rotation, and no cascade semantics on key deletion.

**Gap 4 — No observability hooks for the paid API layer (GPT-4o + Gemini)**
A world-class paid API emits structured metrics: per-key request counts, error rates, latency percentiles, and quota utilization. None of this is present. At minimum, the Terminal API should emit counters that feed a dashboard showing per-customer usage, which is also the foundation of the Sovereign tier if it ships later.

---

## FINAL ACTION PLAN

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0** | Implement `routes_api_terminal.py` with all five Commander endpoints | Missing file | All 3 | Feature does not exist without this |
| **P0** | Implement Stripe subscription route and checkout session creation | Missing file | All 3 | Monetization flow is entirely absent |
| **P0** | Implement Stripe webhook handler for `payment_intent.succeeded` (create key, send email) | Missing file | All 3 | API key delivery is entirely absent |
| **P0** | Implement Stripe webhook handler for subscription cancellation (deactivate key) | Missing file | Gemini + implied All | Revenue protection; users cannot retain access after cancellation |
| **P0** | Implement API key auth middleware checking `X-PP-API-Key` header | Missing file | All 3 | Auth mechanism does not exist |
| **P0** | Remove `try/except` blocks around blueprint registration; make startup fail-hard | `app.py:263–272` | All 3 | Silent failure of paid routes is operationally unacceptable |
| **P0** | Replace global IP-based limiter with per-API-key 1000/day limiter on Terminal endpoints | `app.py:96–97` | All 3 | Wrong identity, wrong quota — direct spec violation |
| **P1** | Set `Cache-Control: private, no-store` for all `/api/v2/terminal/*` responses | `app.py:153–157` | Gemini, GPT-4o | Public caching of authenticated API responses leaks metadata |
| **P1** | Abort startup in production if `SESSION_SECRET` is not set | `app.py:46` | GPT-4o, Grok | Hardcoded fallback key invalidates session security |
| **P1** | Remove `db.create_all()` from startup; use Alembic exclusively | `app.py:243–247` | Gemini, GPT-4o | Concurrent schema managers cause drift and CI failures |
| **P1** | Add `api_key_id` foreign key to `api_usage_log`; keep `key_prefix` as display field | `migration:46–61` | GPT-4o + Gemini (denorm) | Referential integrity required for billing and audit queries |
| **P1** | Implement atomic daily quota increment with timezone-safe reset | Missing endpoint code | GPT-4o, Grok | Race condition allows quota bypass under concurrent load |
| **P1** | Abort startup in production if `STRIPE_SECRET_KEY` or `STRIPE_WEBHOOK_SECRET` are absent | `app.py:72–85` | GPT-4o | Missing payment config should be fatal for a paid feature launch |
| **P2** | Drop redundant `ix_api_keys

---

# WINNER DETERMINATION

# WINNER: GPT-4o

GPT-4o delivered the highest-quality analysis across all four criteria. It was the only model to catch the `public` caching header security vulnerability on API responses, the `db.create_all()` runtime schema drift risk, and the `key_prefix` length ambiguity against the spec — all concrete, line-specific, implementable findings that neither Gemini nor Grok surfaced in Cycle 1. Its recommendations were consistently tied to exact file locations and failure modes, making them immediately actionable, and its Cycle 2 output demonstrated genuine synthesis rather than just restating prior findings.

---

# FINAL SECOND-PASS PRIORITY LIST
*Definitive ordered implementation sequence for v30-terminal-api*

---

## P0 — BLOCKING: DO NOT MERGE UNTIL RESOLVED

**1. Write the missing core implementation files**
The feature does not exist in the review set. Required files:
- `routes_api_terminal.py` — five Commander endpoints:
  - `GET /api/v2/terminal/topics`
  - `GET /api/v2/terminal/sentiment`
  - `GET /api/v2/terminal/signals`
  - `GET /api/v2/terminal/alerts`
  - `POST /api/v2/terminal/subscribe`
- API key auth middleware/decorator
- Stripe subscription route handler
- Stripe webhook handler
*Source: U1 — unanimous, all models*

**2. Replace silent blueprint failure with hard crash**
`app.py:263–272` swallows import errors for the exact launch feature, allowing a "healthy" boot with a dead paid API.

```python
# REMOVE this pattern:
try:
    from routes_api_terminal import terminal_bp
    app.register_blueprint(terminal_bp)
except Exception as e:
    print(f'Terminal API not loaded: {e}')

# REPLACE with:
from routes_api_terminal import terminal_bp
app.register_blueprint(terminal_bp)
```
*Source: U2 — unanimous, all models*

**3. Replace IP-based rate limiter with per-API-key rate limiter**
`app.py:96–97` applies a global IP-based `200/day` limit. The spec requires per-API-key `1000 req/day` for Commander tier. This is both a product-law violation and a billing correctness failure.

```python
# REMOVE:
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day"])

# REPLACE with key-based limiter applied only at the terminal blueprint level:
def get_api_key():
    return request.headers.get("X-API-Key", get_remote_address())

# Apply 1000/day limit per key within routes_api_terminal.py only
```
*Source: Gemini Cycle 1, GPT-4o Cycle 1, confirmed Cycle 2*

---

## P1 — SECURITY: RESOLVE BEFORE ANY PRODUCTION TRAFFIC

**4. Remove `public` cache headers from API responses**
`app.py:153–157` sets `Cache-Control: public` on API route responses. For a paid authenticated API, this risks:
- CDN/proxy caching of user-specific rate-limit metadata
- Cache poisoning
- Data leakage between customers

```python
# For any route matching /api/:
response.headers['Cache-Control'] = 'no-store, private'
```
*Source: GPT-4o Cycle 1 — missed by Gemini and Grok*

**5. Add atomic increment for `requests_today` counter**
The `api_keys.requests_today` field is vulnerable to a race condition under concurrent requests. Two simultaneous requests can both read the same counter value and both write `n+1` instead of `n+2`.

```python
# Use atomic SQL update instead of read-modify-write:
db.session.execute(
    update(ApiKey)
    .where(ApiKey.key_hash == key_hash)
    .values(requests_today=ApiKey.requests_today + 1)
)
```
*Source: Grok Cycle 1, confirmed Gemini Cycle 2*

**6. Add input validation on `subscriber_email`**
`migrations/versions/v30_terminal_api_keys.py:25` stores `subscriber_email` with no format constraint at the schema level. A malformed or empty email will cause silent downstream failures when the system attempts to deliver the API key.

```python
# Add CHECK constraint in migration:
sa.Column('subscriber_email', sa.String(255),
          sa.CheckConstraint("subscriber_email LIKE '%@%.%'"),
          nullable=False)
```
*Source: Grok Cycle 1*

---

## P2 — OPERATIONAL CORRECTNESS

**7. Remove `db.create_all()` runtime call**
`app.py:243–247` calls `db.create_all()` at startup alongside Alembic migrations. This creates schema drift risk: tables created by `create_all()` bypass migration history, masking failures and making rollback unreliable.

```python
# REMOVE db.create_all() from application startup entirely.
# All schema changes must flow exclusively through Alembic migrations.
```
*Source: GPT-4o Cycle 1 — missed by Gemini and Grok*

**8. Verify and fix `key_prefix` length against spec**
`v30_terminal_api_keys.py:23,49` defines `key_prefix` as `String(12)`. The spec key format is `pp_cmd_{32 random chars}`. The literal prefix `pp_cmd_` is 7 characters. Clarify whether this field stores:
- The literal prefix only (`pp_cmd_` = 7 chars → column is oversized but harmless), or
- A truncated portion of the full key for display (`pp_cmd_XXXXX` = 12 chars → verify generation logic matches exactly)

Either interpretation requires confirming the key generation code in the missing implementation file produces values that fit and are consistent with lookup logic.
*Source: GPT-4o Cycle 1*

---

## P3 — SCHEMA / PERFORMANCE HYGIENE

**9. Drop redundant `ix_api_keys_key_hash` index**
`v30_terminal_api_keys.py:39–40` creates both:
- `idx_api_keys_hash_active` — composite index on `(key_hash, active)`
- `ix_api_keys_key_hash` — single-column index on `key_hash`

The composite index satisfies all queries that filter on `key_hash` alone. The single-column index adds write overhead on every insert/update with no read benefit.

```python
# REMOVE from migration:
sa.Index('ix_api_keys_key_hash', 'key_hash'),
```
*Source: Gemini Cycle 1, confirmed GPT-4o Cycle 2*

**10. Remove unrelated files from PR**
The following files are unrelated to `v30-terminal-api` and inflate review scope and risk:
- `media_reforge/static/js/media_unified.js`
- Audit tooling scripts

Move to separate PRs before merge.
*Source: Gemini Cycle 1, GPT-4o Cycle 1*

---

## SUMMARY TABLE

| Priority | Item | Blocking? | Source |
|---|---|---|---|
| P0-1 | Write missing implementation files | ✅ Yes | All models |
| P0-2 | Hard-fail on blueprint import error | ✅ Yes | All models |
| P0-3 | Fix rate limiter to per-key 1000/day | ✅ Yes | Gemini, GPT-4o |
| P1-4 | Remove public cache headers from API | ⚠️ Security | GPT-4o only |
| P1-5 | Atomic increment for requests_today | ⚠️ Security | Grok |
| P1-6 | Validate subscriber_email at schema | ⚠️ Security | Grok |
| P2-7 | Remove db.create_all() from startup | ⚠️ Operational | GPT-4o only |
| P2-8 | Verify key_prefix