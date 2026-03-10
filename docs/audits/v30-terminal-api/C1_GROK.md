### CODE REVIEW REPORT: v30-terminal-api

#### SECTION 1: CORRECTNESS
- **Main User Flow Analysis (Commander Tier API Endpoints):**
  - The provided code includes the setup for API key management and usage logging in the migration script (`migrations/versions/v30_terminal_api_keys.py`), which is a foundational step for the Commander tier API as per the spec. However, the actual implementation of the five specified endpoints (e.g., `/api/v2/terminal/topics`) is not present in the provided files. The `app.py` file registers a blueprint for `terminal_bp` (line 264), but the corresponding code for `routes_api_terminal.py` is missing.
  - **Logic Errors:** Without the endpoint implementations, it's impossible to verify if the logic for data retrieval (e.g., top topics, sentiment scores) is correct. The migration script correctly sets up tables for API keys and usage logs, but there's no evidence of rate limiting logic (1000 req/day for Commander) being implemented yet.
  - **Race Conditions:** The `api_keys` table in the migration script tracks `requests_today` (line 29), but without endpoint code, it's unclear if concurrent requests are handled safely. If multiple requests update this counter simultaneously without proper locking, it could lead to undercounting or overcounting usage.
  - **N+1 Query Problems:** The migration script creates indexes on frequently queried fields like `key_hash` and `subscriber_email` (lines 39-44), which is good. However, without endpoint code, I can't assess if queries are optimized or if N+1 issues exist when validating API keys or logging usage.
  - **Edge Cases:** The migration script doesn't account for scenarios like a full database (no constraints on table size) or invalid email inputs (no validation on `subscriber_email` field, line 25). If an API key is created with an empty or malformed email, downstream processes like sending API keys via email could fail silently.

#### SECTION 2: LAW COMPLIANCE
- **LAW 1: Commander tier ($49/mo) ships first**
  - **PARTIAL** | The migration script (`migrations/versions/v30_terminal_api_keys.py:19-46`) sets up tables for API keys with a `tier` field (line 24) set to support Commander, but no endpoint code is provided to confirm that only Commander tier is implemented. Watcher and Sovereign tiers are not mentioned, which aligns with not building them, but lack of endpoint code makes full compliance unverifiable.
- **LAW 2: API auth via API keys (not JWT, not OAuth)**
  - **PARTIAL** | The migration script supports API key storage with `key_hash` and `key_prefix` (lines 22-23), and indexes for fast lookup (lines 39-40). However, without endpoint code, I can't confirm if authentication is implemented using `X-PP-API-Key` header or if rate limiting (1000 req/day) is enforced. Format `pp_cmd_{32 random chars}` is not explicitly coded in the provided files.
- **LAW 3: Five Commander endpoints**
  - **VIOLATION** | None of the five specified endpoints (`/api/v2/terminal/topics`, etc.) are implemented in the provided code. `app.py:264` registers a `terminal_bp` blueprint, but the corresponding file is missing, so no compliance is evident.
- **LAW 4: Stripe integration for Commander**
  - **VIOLATION** | The migration script includes fields for Stripe data (`stripe_customer_id`, `stripe_subscription_id`, `stripe_session_id`, lines 26-28), but there’s no code in `app.py` or elsewhere to handle Stripe webhooks or create API keys upon `payment_intent.succeeded`. No `/api/v2/terminal/subscribe` endpoint is provided for Stripe Checkout session creation.
- **LAW 5: Response format consistent across endpoints**
  - **VIOLATION** | Without endpoint implementations, there’s no evidence that responses follow the specified JSON structure with fields like `tier`, `endpoint`, `timestamp`, `cache_age_seconds`, `data`, and `rate_limit`. The structure is not hardcoded or referenced in any provided file.

#### SECTION 3: SECURITY
- **SQL Injection:** The migration script uses SQLAlchemy’s ORM for table creation (`migrations/versions/v30_terminal_api_keys.py:19-62`), which is safe from injection by design. However, without endpoint code, I can't verify if user inputs (e.g., API key validation or email) are sanitized before queries.
- **Authentication Bypasses:** No endpoint code is provided, so I can't assess if routes are properly guarded by API key checks. If `terminal_bp` lacks auth middleware, unauthorized access could occur.
- **Rate Limiting Gaps:** The `api_keys` table tracks `requests_today` (line 29), but without endpoint logic, I can't confirm if the 1000 req/day limit is enforced. A malicious user could potentially exhaust limits if no throttling is implemented.
- **Secrets in Code:** No hardcoded secrets are found in the provided files. `app.py:46` uses environment variables for sensitive data like `SESSION_SECRET`, which is correct. However, without Stripe integration code, I can't verify if `STRIPE_SECRET_KEY` is securely handled.
- **Unvalidated User Input:** The migration script doesn't enforce constraints on `subscriber_email` (line 25), which could allow invalid data into the DB. Without endpoint code, I can't check if inputs are validated before storage or usage.

#### SECTION 4: FRONTEND QUALITY
- **UI Match to Spec:** No frontend code specific to the v30-terminal-api feature is provided (e.g., no UI for subscribing or viewing API usage). The `media_reforge/static/js/media_unified.js` file is unrelated to this feature and focuses on a media dashboard, not API interaction.
- **Hardcoded Values:** Not applicable as no relevant frontend code is provided.
- **Mobile Viewport Breakage:** Not applicable due to lack of frontend code.
- **JS Errors:** Not applicable due to lack of relevant frontend code.
- **Loading/Error/Empty States:** Not applicable due to lack of frontend code.
- **World-Class Look:** Not applicable due to lack of frontend code. However, the absence of any user-facing component for API subscription or management is a significant gap for a premium product.

#### SECTION 5: BACKEND QUALITY
- **DB Operations (Try/Except with Rollback):** The migration script (`migrations/versions/v30_terminal_api_keys.py`) is purely declarative and doesn't include transactional logic. Without endpoint code, I can't verify if DB writes (e.g., API key creation, usage logging) are wrapped in try/except with rollbacks.
- **External API Calls (Timeout/Retry/Degradation):** No Stripe integration or external API call code is provided, so I can't assess if timeouts or retries are handled for Stripe webhooks or Checkout sessions.
- **Cron Job Handling:** No cron jobs related to this feature (e.g., resetting `requests_today`) are evident in the provided code, so failure handling can't be assessed.
- **Memory Leaks:** Without endpoint code, I can't identify per-request memory issues. The migration script itself is static and poses no risk.
- **Logging:** `app.py:27-32` sets up logging, but without endpoint code, I can't confirm if API errors (e.g., invalid key, rate limit exceeded) are logged with sufficient context.

#### SECTION 6: WORLD-CLASS GAP ANALYSIS
- **Comparison to Bloomberg Terminal/Coinbase Advanced/Blockworks:**
  - **API Endpoint Implementation:** A world-class product would have fully implemented, documented endpoints with robust error handling and real-time data feeds. The complete absence of the five Commander endpoints is a critical gap.
  - **Stripe Integration:** Professional platforms integrate payment systems seamlessly with immediate API key delivery post-payment. No such integration exists here.
  - **Rate Limiting and Usage Analytics:** Premium services provide detailed usage dashboards for API consumers. The `api_usage_log` table (line 47-61) is a start, but no frontend or API to expose this data to users is provided.
  - **Data Freshness and Caching:** The spec mentions `cache_age_seconds` in responses, but without code, I can't verify if data is cached appropriately or if freshness is guaranteed for critical endpoints like `/api/v2/terminal/breaking`.
  - **Security and Compliance:** World-class products implement strict security headers and compliance with GDPR/CCPA for user data. `app.py:134-139` adds some security headers, but without endpoint code, I can't assess full compliance or API-specific protections.
  - **Excellent Areas:** The migration script's indexing strategy (`migrations/versions/v30_terminal_api_keys.py:39-44, 58-61`) is well-designed for performance, aligning with professional standards for DB optimization.

#### SECTION 7: SCORES (0-100 each)
- Backend Logic:    20/100 (Migration script is correct, but core endpoint logic is missing)
- Frontend/UI:      0/100 (No frontend for API subscription or management provided)
- Error Handling:   10/100 (No evidence of error handling in endpoints or Stripe integration)
- Security:         30/100 (Basic DB setup is secure, but no auth or rate limiting code to review)
- Performance:      40/100 (Good indexing in migration, but no endpoint code to assess scalability)
- Law Compliance:   10/100 (Only partial compliance with LAW 1 and 2; others violated due to missing code)
- World-Class Gap:  5/100 (Significant gaps in implementation compared to professional standards)
- OVERALL:          16/100 (Incomplete feature with critical components missing)

#### SECTION 8: PRIORITY ACTION PLAN
- P0 CRITICAL | Implement the five Commander endpoints | [routes_api_terminal.py:missing] | Without these, the feature is non-functional and cannot serve users.
- P0 CRITICAL | Add Stripe integration for webhook and Checkout session | [app.py:missing] | Payment processing and API key delivery are core to monetization and user onboarding.
- P0 CRITICAL | Enforce API key authentication and rate limiting (1000 req/day) | [routes_api_terminal.py:missing] | Without this, security and usage control are compromised, risking abuse.
- P1 HIGH     | Develop frontend for subscription and API key management | [missing file] | Users need a way to subscribe and view usage, critical for user experience.
- P1 HIGH     | Ensure response format matches LAW 5 spec | [routes_api_terminal.py:missing] | Consistency in API responses is key to developer trust and usability.
- P2 MEDIUM   | Add validation for subscriber_email in DB | [migrations/versions/v30_terminal_api_keys.py:25] | Prevents invalid data from breaking email delivery or analytics.
- P2 MEDIUM   | Implement usage analytics dashboard for API consumers | [missing file] | Enhances user value by providing transparency on API usage.
- P3 LOW      | Add logging for API errors with detailed context | [routes_api_terminal.py:missing] | Improves debugging and monitoring in production.

#### SECTION 9: THE ONE THING
Implement the five Commander endpoints with proper authentication and rate limiting to make this feature functional and secure, as their absence renders the entire API unusable.

#### SECTION 10: FINAL VERDICT
This code is not ready for production due to the complete absence of the core API endpoints and Stripe integration necessary for the Commander tier functionality. Before deployment, the five specified endpoints must be implemented, Stripe payment processing and webhook handling must be added, and API key authentication with rate limiting must be enforced.