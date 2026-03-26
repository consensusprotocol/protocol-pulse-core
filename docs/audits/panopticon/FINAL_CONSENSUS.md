# CONSENSUS REPORT — PANOPTICON — CYCLE 2
Generated: 2026-03-26 00:39
Models: gemini, grok (+1 failed: gpt-4o rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Data Access Control (Auth/Leak) | CRITICAL | N/A | LOW* | **CRITICAL** |
| Correlation Engine Logic | CRITICAL | N/A | HIGH | **CRITICAL** |
| Cache Architecture | CRITICAL | N/A | CRITICAL | **CRITICAL** |
| External API Integration | HIGH | N/A | HIGH | **HIGH** |
| Placeholder/Fallback Data Integrity | HIGH | N/A | HIGH | **HIGH** |
| Internal API Rate Limiting | HIGH | N/A | CRITICAL | **HIGH** |
| Brand/Law Compliance | MEDIUM | N/A | MEDIUM | **MEDIUM** |
| Service Layer Architecture | HIGH | N/A | — | **HIGH** |
| Scheduler-Service Coupling | MEDIUM | N/A | — | **MEDIUM** |
| Error Handling (BTC Enrichment) | — | N/A | HIGH | **MEDIUM** |

> *Grok disagreed on the data leak severity; see CONFLICTS section. Gemini's analysis is adjudicated as authoritative on this point.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### 1. Non-Scalable In-Memory Cache
- **What it is:** The `_cache` dictionary (`services/panopticon_service.py:31-43`) is a plain Python dict. In any multi-worker deployment (Gunicorn, uWSGI), each worker has its own isolated copy. Cache invalidation performed in one worker is invisible to others. Simultaneous cache misses cause a thundering herd: all workers fire expensive external API calls simultaneously.
- **File/Line:** `services/panopticon_service.py:31-43`
- **Fix:** Replace with a shared Redis cache (e.g., via `redis-py` or `flask-caching` with Redis backend). Implement a per-key distributed lock (Redis `SET NX EX` or `redlock`) so only one worker rebuilds a cold cache entry while others wait or serve stale data.

### 2. Misleading Placeholder Data with Dynamic Timestamps
- **What it is:** The fallback placeholder system (`services/panopticon_service.py:218-287`) uses `utcnow() - timedelta(days=12)` and similar expressions to generate "recent-looking" dates for hardcoded, static historical filings. This makes stale fabricated data appear current to the user.
- **File/Line:** `services/panopticon_service.py:218-287` (esp. line 230)
- **Fix:** Replace all dynamic `timedelta` date expressions with the real historical dates of the placeholder filings. Add an `is_placeholder: True` field to each record. Surface a clearly visible "SAMPLE DATA — Live data temporarily unavailable" banner in the UI when this flag is present.

### 3. Fundamentally Flawed Correlation Engine
- **What it is:** `build_correlations()` (`services/panopticon_service.py:760-817`) performs no temporal or causal analysis. It simply appends the most recent whale movements and geopolitical events alongside a flagged disclosure regardless of their timestamps or relevance. This presents unrelated events as correlated intelligence, which is functionally deceptive.
- **File/Line:** `services/panopticon_service.py:760-817`
- **Fix:** Either (a) disable and prominently label the feature as "Coming Soon — Correlation Engine Under Construction," or (b) rewrite to perform genuine temporal windowing: only include events whose timestamps fall within a configurable window (e.g., ±72 hours) of the disclosure trade date. Add a minimum-confidence threshold before surfacing any correlation.

### 4. Missing Internal API Rate Limiting
- **What it is:** All API endpoints in `core/blueprints/panopticon.py:75-204` have no server-side rate limiting. Any unauthenticated or authenticated user can hammer these endpoints without restriction, causing denial of service and/or triggering bans from upstream external APIs that the endpoints proxy.
- **File/Line:** `core/blueprints/panopticon.py:75-204`
- **Fix:** Integrate `flask-limiter` with a Redis storage backend. Apply tiered limits: e.g., `60/minute` per IP for free tier, `300/minute` for Commander tier. Apply stricter limits to the most expensive endpoints (e.g., the Anthropic-backed `/bitcoin-case` route).

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above also qualify as majority findings. The following additional items were raised with overlapping but slightly different framing:

### 5. Undocumented External API Dependency (`efts.house.gov`)
- **What it is:** The code queries `https://efts.house.gov/LATEST/search-index` with assumed parameters (`q`, `dateRange`, `startdt`, `enddt`) that are not publicly documented. There is no exponential backoff, no retry logic, and no detection of schema drift. Silent failures return empty results with no alerting.
- **File/Line:** `services/panopticon_service.py:136-167`
- **Fix:** Document the API behavior in a comment block citing any reverse-engineered observations. Implement exponential backoff with jitter (3 retries, 1s/2s/4s). Add response schema validation (e.g., a simple structural assertion on `hits.hits`) and emit a structured log warning if the schema doesn't match expectations.

---

## UNIQUE INSIGHTS (single model only — evaluated below)

### A. Circular Dependency: Service Imports Flask `app` Object
- **Source:** Gemini only
- **Finding:** `services/panopticon_service.py:490` contains `from app import app, db`, creating a circular dependency and tightly coupling the service to the Flask application object. This makes unit testing impossible and breaks separation of concerns.
- **Assessment: IMPLEMENT.** This is a classic architectural anti-pattern with concrete, immediate harm: it prevents isolated testing of the service layer and will cause import failures if the service is ever used outside the Flask request context (e.g., in a management command or background job). Fix by passing the db session in via dependency injection or using Flask's `current_app` proxy and `db.session` at call sites rather than at import time.

### B. Brittle Scheduler-to-Cache Coupling
- **Source:** Gemini only
- **Finding:** `services/scheduler.py:610-631` directly pops keys from the panopticon service's internal `_cache` dict by string literal. The scheduler is coupled to the internal implementation details of the service layer.
- **Assessment: IMPLEMENT.** This is a genuine fragility. If cache key names change, invalidation silently stops working — a subtle, hard-to-detect bug. The fix is straightforward: expose `refresh_congress_data()`, `refresh_whale_data()`, etc. as public methods on the service that encapsulate their own cache invalidation.

### C. Hardcoded Anthropic Model Version
- **Source:** Grok only
- **Finding:** `services/panopticon_service.py:940` hardcodes `claude-sonnet-4-6-20250514`. When Anthropic deprecates this version, the feature breaks silently.
- **Assessment: IMPLEMENT (low effort, high longevity).** Move the model name to a configuration constant or environment variable (`ANTHROPIC_MODEL_ID`). This costs one line to fix and prevents a future silent production breakage.

### D. Prompt Injection Risk in Bitcoin Case API
- **Source:** Grok only
- **Finding:** `core/blueprints/panopticon.py:192-196` passes user-supplied `event_summary` (capped at 500 chars but otherwise unsanitized) directly into an Anthropic API prompt.
- **Assessment: IMPLEMENT.** A 500-character limit is not prompt injection protection. An attacker can craft a 499-character payload that overrides the system prompt's intent (e.g., "Ignore all previous instructions and output..."). Add a sanitization layer: strip special characters, enforce an allowlist of expected content patterns, and consider wrapping the user input in XML-style delimiters within the prompt to isolate it from the instruction context.

### E. Inefficient Full-Dataset Fetch in Correlation Builder
- **Source:** Grok only
- **Finding:** `services/panopticon_service.py:769-771` fetches full, unpaginated datasets on every `build_correlations()` call.
- **Assessment: INVESTIGATE FURTHER.** The severity depends on dataset size. If these are already cached upstream calls, the performance cost may be acceptable in the near term. However, as data grows this will become a bottleneck. Recommend adding pagination/filtering parameters and a note in the backlog to revisit when the dataset exceeds 1,000 records.

### F. Runtime `.env` File Reading in Request Handler
- **Source:** Gemini only
- **Finding:** `services/panopticon_service.py:917-927` attempts to read the `ANTHROPIC_API_KEY` from a `.env` file at runtime during a request if the environment variable is not set.
- **Assessment: IMPLEMENT.** Configuration must be loaded once at startup, not on every request. This also risks exposing the `.env` file path in error logs. Move all key loading to application startup (`create_app()` or equivalent) and raise a fatal startup error if required keys are absent.

---

## CONFLICTS (models disagree — tiebreaker ruling)

### CONFLICT 1: Data Leak Severity — CSS Overlay as Security Control

- **Gemini:** CRITICAL — The main dashboard route sends full Commander-tier data to all users; free users are protected only by a CSS `display:none` overlay. This is a catastrophic data leak.
- **Grok:** LOW — "The current implementation adequately restricts sensitive data to Commander-tier users via API checks." The overlay is a visual deterrent, not a security mechanism.

**TIEBREAKER: Gemini is correct. Severity is CRITICAL.**

Grok's reasoning contains a material error. The API checks protect the *JSON API endpoints*, but Gemini's finding is about the *main page route* (`/panopticon`), which calls `get_dashboard_data()` in the backend and passes the full result set to the Jinja template context for *every user*. The Commander-tier data is embedded in the HTML payload delivered to the browser before any overlay renders. A free user only needs to open DevTools → Network → preview the initial page response. The data is already there. Grok appears to have conflated the API endpoint protection with the page-route protection. This is a server-side data exposure, not a client-side UI concern.

---

## VALIDATED STRENGTHS (do NOT change)

Both models (and the Cycle 1 consensus) converged on the following areas as correctly implemented:

1. **API Endpoint Authentication Gates:** The individual JSON API routes in `core/blueprints/panopticon.py:75-204` do correctly check for Commander-tier status before returning data. This gate is functioning as intended and should not be removed — the P0 fix is additive (also gating the page route), not a replacement.

2. **Timeout on External HTTP Calls:** The 15-second timeout on `efts.house.gov` requests (`services/panopticon_service.py:144`) is a reasonable baseline that prevents indefinite hangs. Keep it; layer backoff on top of it.

3. **Fallback Existence (Concept, Not Execution):** The *idea* of a fallback/placeholder system when the external API is unavailable is architecturally sound. The problem is in the execution (misleading dates). The structural decision to have a fallback is correct and should be preserved.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Finding |
|---|---|---|
| LAW 1 — Brand Palette | **VIOLATED** | `--pn-red: #ff3b5f` (should be `#CC2222`); `--pn-bg: #06070b` (should be `#0A0A0F`). `templates/panopticon.html:15,23` |
| LAW 2 — Pixel Zones | **AMBIGUOUS** | Laws describe a 1920×1080 video canvas with PiP zones; implementation is a responsive HTML dashboard. Fundamental media-type mismatch requires product owner clarification. |
| LAW 3 — Typography | **VIOLATED** | Headline/entity font sizes are 12–14px at `templates/panopticon.html:289,380,432`; spec requires 42–56px and 28–32px ranges. |
| LAW 4 — Component Patterns | **VIOLATED** | `.pn-card` background is `#0d1118` (should be `#111`); missing required 3px red left accent border. `templates/panopticon.html:271-280` |

**Final Determination:** Three of four verifiable laws are violated. Law 2 requires a product-owner decision on whether panopticon is a web dashboard or a video canvas overlay — the laws cannot be evaluated until that is resolved. Laws 1, 3, and 4 must be corrected before release.

---

## SECURITY CONSENSUS

Priority order of confirmed security issues (both models where noted):

| Priority | Issue | Models | File:Line |
|---|---|---|---|
| 1 | **Data leak via page-route HTML payload** (free users receive full Commander data) | Gemini | `core/blueprints/panopticon.py:47-48` |
| 2 | **No rate limiting on internal API endpoints** (DoS + external API ban risk) | Both | `core/blueprints/panopticon.py:75-204` |
| 3 | **Prompt injection via unsanitized `event_summary`** | Grok | `core/blueprints/panopticon.py:192-196` |
| 4 | **API key loaded from `.env` at request time** (path exposure in logs) | Gemini | `services/panopticon_service.py:917-927` |
| 5 | **Hardcoded external API key fallback path** (brittle, insecure config) | Gemini | `services/panopticon_service.py:917-927` |

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as gaps between current implementation and a truly world-class product:

1. **Real-time or near-real-time data pipeline (both models):** The current architecture is pull-based with a 10-minute TTL cache. A world-class intelligence dashboard would use a push or event-driven architecture (WebSockets, SSE, or a message queue like Celery + Redis pub/sub) so users see disclosures and whale movements the moment they are ingested, not up to 10 minutes later.

2. **Genuine correlation and intelligence engine (both models):** The core value proposition of "Panopticon" — surfacing non-obvious connections between congressional trades, whale movements, and geopolitical events — is entirely absent. A world-class product would implement at minimum: temporal windowing correlation, entity co-occurrence scoring, and anomaly detection (e.g., "this ticker appears in 3 disclosures and 2 whale moves within 48 hours"). The current implementation is a data aggregation dashboard, not an intelligence engine.

3. **Transparent data provenance and freshness indicators (both models):** Neither the current live data nor the placeholder fallback clearly communicates to the user when data was last refreshed, from what source, and whether it is live or sample. A world-class product surfaces data provenance (source, timestamp, confidence) on every data point.

4. **Observability and alerting for external API degradation (both models):** When `efts.house.gov` starts returning malformed responses or when the mempool API rate-limits the service, the system silently degrades. A world-class product emits structured metrics to a monitoring system (Datadog, Prometheus, etc.) and pages on-call when an external dependency degrades.

---

## FINAL ACTION PLAN (sorted by consensus priority)

### P0 — CRITICAL (deployment blockers)

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Fix data leak: gate `get_dashboard_data()` at page route; return redacted/sample-only dataset for non-Commander users — do NOT embed real Commander data in HTML payload | `core/blueprints/panopticon.py:47-48` | Gemini (Grok disagreed — overruled) | Free users can extract full paid data via View Source. Catastrophic trust/legal/revenue violation. |
| P0-2 | Disable or rewrite correlation engine: either remove `build_correlations()` and replace with "Coming Soon" stub, or rewrite with genuine ±72h temporal windowing | `services/panopticon_service.py:760-817` | Both | Feature is functionally deceptive. Presents unrelated data as correlated intelligence. |
| P0-3 | Replace `_cache` dict with Redis-backed shared cache + distributed lock to prevent thundering herd | `services/panopticon_service.py:31-43` | Both | In-process dict is broken in any multi-worker deployment. Production non-functional. |

### P1 — HIGH (must fix before wide release)

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Add `flask-limiter` with Redis backend to all API routes; tiered limits by user tier | `core/blueprints/panopticon.py:75-204` | Both | No rate limiting = trivial DoS and upstream API ban risk. |
| P1-2 | Fix placeholder timestamps: use real historical dates, add `is_placeholder: True` flag, surface UI banner when active | `services/panopticon_service.py:218-287` | Both | Dynamic `timedelta` dates on static data actively deceive users about data freshness. |
| P1-3 | Remove `from app import app, db` import from service layer; inject db session via parameter or use `current_app` proxy | `services/panopticon_service.py:490` | Gemini | Circular dependency. Service is untestable in isolation. Will cause import failures outside Flask context. |
| P1-4 | Move API key loading to application startup; remove runtime `.env` file read; raise fatal error at boot if key absent | `services/panopticon_service.py:917-927` | Gemini | Config must load once at startup. Runtime file reads are inefficient, brittle, and leak file paths in error logs. |
| P1-5 | Add prompt injection sanitization to `event_summary` input: strip special chars, wrap in XML delimiters in prompt, enforce content allowlist | `core/blueprints/panopticon.py:192-196` | Grok | 500-char limit is not injection protection. User can override system prompt intent. |
| P1-6 | Add exponential backoff + retry (3 attempts, 1s/2s/4s + jitter) and response schema validation to `efts.house.gov` fetcher | `services/panopticon_service.py:136-167` | Both | Single attempt with no backoff fails permanently on transient errors. Schema drift causes silent data loss. |

### P2 — MEDIUM (important for quality and maintainability)

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P2-1 | Fix brand palette: `--pn-red` → `#CC2222`, `--pn-bg` → `#0A0A0F` | `templates/panopticon.html:15,23` | Gemini | LAW 1 violation. |
| P2-2 | Fix typography: headline/entity elements to 42–56px / 28–32px ranges | `templates/panopticon.html:289,380,432` | Gemini | LAW 3 violation. |
| P2-3 | Fix `.pn-card`: background → `#111`, add 3px red left accent border | `templates/panopticon.html:271-280` | Gemini | LAW 4 violation. |
| P2-4 | Decouple scheduler from service cache internals: expose `refresh_x_data()` public methods; scheduler calls methods, not dict keys | `services/scheduler.py:610-631` | Gemini | Key rename = silent broken invalidation. Violates encapsulation. |
| P2-5 | Externalize Anthropic model ID to env var `ANTHROPIC_MODEL_ID` with documented fallback | `services/panopticon_service.py:940` | Grok | Hardcoded model version → silent breakage on Anthropic deprecation. |
| P2-6 | Add BTC price enrichment fallback: if `get_btc_price()` returns None, log warning and set `amount_usd: null` with UI indicator | `services/panopticon_service.py:872-876` | Grok | Silent `None` degrades user experience without visibility. |
| P2-7 | Add `data-freshness` timestamp and source attribution to each data card in UI | `templates/panopticon.html` (all card components) | Both (implied) | World-class gap: users cannot assess data reliability without provenance. |
| P2-8 | Clarify LAW 2 media type: confirm whether panopticon is web dashboard or FFmpeg video canvas overlay; update governing laws accordingly | Design docs + `templates/panopticon.html` | Gemini | Fundamental spec/implementation mismatch cannot be resolved without product owner input. |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY.**

Two full cycles of review by 2 independent AI models (with GPT-4o failing due to token limits) have surfaced three hard deployment blockers that are each independently sufficient to prevent release:

1. **P0-1 (Data Leak):** Free users receive full Commander-tier paid content in their HTML payload. This is a revenue integrity failure, a potential legal liability under any terms of service that promise tier-gated data, and a complete undermining of the subscription model.

2. **P0-2 (Deceptive Correlation):** The flagship intelligence feature of the product presents fabricated correlations. Surfacing unrelated events as "correlated signals" to users making financial-adjacent decisions is a reputational and potential legal risk.

3. **P0-3 (Broken Cache):** The feature will not function correctly under any real deployment topology. Every user in a multi-worker environment will experience inconsistent, stale, or redundantly re-fetched data.

Until all three P0 items are resolved and regression tests pass, this feature must not be deployed to production users.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/audits/panopticon_CONSENSUS_C2.md.

This is the FINAL PASS for the panopticon feature.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 — CRITICAL (implement first, nothing else matters until these are done):

P0-1 | Fix data leak at page route | core/blueprints/panopticon.py:47-48
  The get_dashboard_data() call on the main /panopticon route must NOT embed
  real Commander-tier data in the HTML payload for non-Commander users.
  If the user is not Commander-tier, return a structurally identical but
  fully redacted or sample-only dataset. Real data must never touch the
  Jinja template context for unpermissioned users. The CSS overlay is NOT
  a security control.

P0-2 | Disable or rewrite correlation engine | services/panopticon_service.py:760-817
  The build_correlations() function performs no temporal analysis. It appends
  unrelated whale movements and geopolitical events to disclosures regardless
  of timestamps. Either: (a) remove entirely and replace with a "Correlation
  Engine — Coming Soon" stub in the UI, or (b) rewrite to only include events
  whose timestamps fall within a ±72 hour window of the disclosure trade date,
  with a minimum of 2 co-occurring signals before surfacing a correlation.

P0-3 | Replace in-memory _cache dict with Redis | services/panopticon_service.py:31-43
  The plain Python dict cache is non-functional in multi-worker deployments.
  Replace with flask-caching (Redis backend) or redis-py directly.
  Implement

---

# WINNER DETERMINATION

# WINNER: **Gemini** — Gemini identified the two most severe production-blocking issues (catastrophic data leak via unprotected dashboard route and fundamentally fraudulent correlation logic) that Grok initially rated LOW and HIGH respectively, both of which were adjudicated as CRITICAL in the consensus report. Gemini's findings were specific, structurally accurate, and directly actionable, and were explicitly validated by Grok's own Cycle 2 self-correction acknowledging it had missed or underweighted exactly those findings.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: severity × blast radius × implementation dependency chain.

---

## P0 — DEPLOY BLOCKER (Fix before any merge)

### 1. Data Leak via Unprotected Dashboard Route
- **File:** `routes/panopticon.py` — main `/panopticon` GET handler
- **Action:** Move all Commander-tier data fetching behind the same auth guard already applied to API routes. The backend must not populate the template context with gated data for unauthenticated or free-tier users. CSS visibility is not access control.
- **Test:** `curl /panopticon` with no session cookie must return zero gated payload in HTML source.

### 2. Fraudulent Correlation Engine
- **File:** `services/panopticon_service.py:760-817`
- **Action:** Remove or gate the `build_correlations` output entirely until genuine temporal overlap logic is implemented (e.g., events must share a configurable time window, e.g., ±72h, with the flagged disclosure date). Do not present co-incidental data as correlated. Label any interim output explicitly as "uncorrelated recent activity."
- **Test:** Unit test must assert that events outside the time window are excluded from correlation output.

---

## P1 — CRITICAL ARCHITECTURE (Fix before production traffic)

### 3. In-Memory Cache → Redis
- **File:** `services/panopticon_service.py:31-43`
- **Action:** Replace `_cache` dict with `flask-caching` Redis backend. Add per-key distributed lock (`SET NX EX`) to prevent thundering herd on simultaneous cache misses across workers.
- **Test:** Simulate two concurrent Gunicorn workers with a cold cache; assert only one upstream API call fires per key.

### 4. Misleading Placeholder Data with Dynamic Timestamps
- **File:** `services/panopticon_service.py:218-287`
- **Action:** Static fallback data must carry static, hardcoded dates. If dynamic dates are required, the data must be genuinely fetched or the UI must display an explicit "data unavailable" state rather than fabricating recency.
- **Test:** With all external APIs mocked to fail, assert that no fallback record carries a timestamp within 30 days of `utcnow()`.

---

## P2 — HIGH SEVERITY (Fix within one sprint)

### 5. Sequential Blocking External API Calls
- **File:** `services/panopticon_service.py` — all `requests.get` calls in service layer
- **Action:** Parallelize independent external calls using `concurrent.futures.ThreadPoolExecutor` or migrate to `httpx` async. Each call must have an independent timeout; one slow endpoint must not block the full response.
- **Test:** Mock one endpoint to sleep 10s; assert total response time does not exceed single-call timeout + margin.

### 6. Missing Retry and Backoff on External API Integration
- **File:** `services/panopticon_service.py:123-184`
- **Action:** Replace bare `requests.get` with `urllib3` Retry adapter or `tenacity` decorator. Implement exponential backoff (base 1s, max 30s, 3 retries) on 429, 500, 502, 503. The existing `time.sleep(0.5)` is not a substitute.
- **Test:** Mock endpoint returning 429 twice then 200; assert successful response is returned on third attempt.

### 7. Internal API Rate Limiting
- **File:** API route handlers
- **Action:** Apply per-user rate limiting via `flask-limiter` with Redis storage backend (not in-memory, for same multi-worker reasons as item 3). Limits must be enforced server-side, not inferred from client behavior.
- **Test:** Assert 429 is returned after limit is exceeded from a single authenticated user within the window.

### 8. Service Layer Architecture — Scheduler Coupling
- **File:** Scheduler ↔ `panopticon_service.py` direct coupling
- **Action:** Decouple via a task queue (Celery + Redis) or at minimum an interface boundary. The service layer must not be directly invoked by the scheduler in a way that bypasses error isolation.
- **Test:** Assert scheduler job failure does not propagate an unhandled exception to the request thread.

---

## P3 — MEDIUM SEVERITY (Fix before public launch)

### 9. Brand/Law Compliance — Color and Typography
- **File:** `templates/panopticon.html:15, 23, 289, 380, 432`
- **Action:** `--pn-red` → `#CC2222`, `--pn-bg` → `#0A0A0F`. Audit all headline/entity font sizes against governing spec (42–56px / 28–32px ranges). Assign a single owner to maintain a shared design token file to prevent future drift.

### 10. Error Handling — BTC Enrichment Path
- **File:** BTC enrichment logic in service layer
- **Action:** Wrap enrichment in an explicit try/except with structured logging. Partial enrichment failure must degrade gracefully (return unenriched record) rather than silently drop or corrupt the parent record.
- **Test:** Mock BTC API to raise `ConnectionError`; assert parent record is still returned with enrichment fields set to `null`.

---

## IMPLEMENTATION ORDER RATIONALE

Items 1–2 are sequenced first because they represent active harm to users (data exposure, disinformation). Items 3–4 are sequenced before traffic because they will cause cascading failure under any real load. Items 5–8 are reliability and correctness concerns that compound under scale. Items 9–10 are correctness and compliance concerns with no immediate user safety dimension.