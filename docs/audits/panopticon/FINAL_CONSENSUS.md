# CONSENSUS REPORT — PANOPTICON — CYCLE 2
Generated: 2026-03-26 00:53
Models: grok, gemini (+1 failed: gpt-4o — TPM limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Congressional Data Fetching (Q1) | HIGH | N/A | HIGH | **HIGH** |
| API Rate Limiting (Q2) | CRITICAL | N/A | CRITICAL | **CRITICAL** |
| Cache Architecture | CRITICAL | N/A | CRITICAL | **CRITICAL** |
| Fallback / Placeholder Data Quality | CRITICAL | N/A | HIGH | **CRITICAL** (Gemini upgraded; rationale accepted) |
| Classified Overlay / Demo Mode Security | PASS | N/A | PASS | **PASS** |
| External API Schema Robustness | HIGH | N/A | HIGH | **HIGH** |
| LLM Prompt Injection Defense | HIGH | N/A | not scored | **HIGH** |
| Overall Production Readiness | 3/10 | N/A | 4/10 | **3.5/10 — NOT PRODUCTION READY** |

> **Note on scoring validity:** GPT-4o failed due to token limit. All consensus determinations below are drawn from 2-model agreement (Gemini + Grok). Where only one model raised a finding, it is flagged explicitly as a unique insight.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — In-Memory Rate Limiter is Multi-Process Broken
**What it is:** `_rate_limit_store` is a plain Python dictionary in `core/blueprints/panopticon.py:29`. In any multi-worker deployment (Gunicorn, uWSGI), each worker process holds its own isolated copy of this dictionary. A user whose requests are load-balanced across workers can exceed the intended rate limit by a factor equal to the number of workers, rendering the protection completely ineffective.

**File/Line:** `core/blueprints/panopticon.py:29, 36–63`

**What to change:** Remove `_rate_limit_store` entirely. Replace with `Flask-Limiter` configured against a Redis backend. Example:
```python
# core/blueprints/panopticon.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")

@panopticon_bp.route("/api/panopticon/whale-alerts")
@limiter.limit("30/minute")
def whale_alerts():
    ...
```
All per-IP state lives in Redis and is visible to every worker.

---

### U2 — In-Memory Cache is Non-Shared Across Workers
**What it is:** `_cache` is a plain Python dictionary in `services/panopticon_service.py:35–72`, protected by a `threading.Lock`. In a multi-process deployment, every worker has its own private cache, so each worker independently makes full upstream API calls on every cache miss. This multiplies outbound request volume by the number of workers, dramatically increasing the probability of hitting CoinGecko and mempool.space rate limits, and makes the courtesy sleep (`panopticon_service.py:223`) insufficient protection.

**File/Line:** `services/panopticon_service.py:35–72`

**What to change:** Migrate to Redis with TTL-based expiry via `redis-py` or `Flask-Caching[redis]`. The `_cache_lock` can be removed because Redis operations are atomic.
```python
# services/panopticon_service.py
import redis, json
_redis = redis.Redis(host="localhost", port=6379, decode_responses=True)

def _cache_get(key):
    val = _redis.get(key)
    return json.loads(val) if val else None

def _cache_set(key, value, ttl_seconds):
    _redis.setex(key, ttl_seconds, json.dumps(value))
```

---

### U3 — efts.house.gov is an Undocumented Internal Endpoint
**What it is:** The URL `https://efts.house.gov/LATEST/search-index` (`panopticon_service.py:193`) is the search backend for the House website's own front end, not a public API. It carries no SLA, no documented parameters, no versioning contract, and no formal rate limit. It can change or disappear without notice, silently breaking the feature's entire primary data tier.

**File/Line:** `services/panopticon_service.py:193`

**What to change:**
1. Add an explicit code comment documenting the instability and the date it was last verified working.
2. Implement an external health-check monitor (e.g., Uptime Robot, Datadog synthetic) that fires a PagerDuty / Slack alert if the endpoint returns non-200 or if `SCHEMA_DRIFT` log warnings spike above threshold.
3. Proactively evaluate whether the FD&C Act's official [Senate eFD portal](https://efdsearch.senate.gov) or ProPublica Congress API can serve as a more stable primary source.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All three unanimous findings above are simultaneously majority findings. No additional findings reached 2-of-2 agreement beyond U1–U3 and the items below (which were raised by both models in their Cycle 2 output):

### M1 — Placeholder Data Uses Future Dates
**What it is:** `_generate_disclosure_placeholders()` (`panopticon_service.py:296–364`) populates fallback data with dates such as "2025-09-15" and "2025-10-01." From the product's operational date (2026), these are events that have not yet occurred — or are presented as historical when their dates are in the near future. Both models flagged this as damaging to user trust. Gemini upgraded it to CRITICAL; Grok rated it HIGH.

**Consensus ruling:** Treat as **P0 CRITICAL** — accepted Gemini's escalation. An "intelligence" platform presenting future-dated congressional filings as retrieved historical data is not a cosmetic issue; it is a data integrity failure that would immediately destroy credibility if noticed by any politically-aware user.

**File/Line:** `services/panopticon_service.py:296–364`

**What to change:** Replace all placeholder dates with verifiably real, publicly documented historical congressional stock disclosure dates (e.g., known Nancy Pelosi or Dan Crenshaw filings from 2022–2023 that are on the public record). Values can be drawn from propublica.org or the official FD&C Act disclosure archive.

---

## UNIQUE INSIGHTS (single model — evaluate carefully)

### UI-1 — Broken Scheduler Cache-Warming (Gemini only)
**What it is:** Gemini identified that the scheduled background task in `services/scheduler.py:607` (`panopticon_congress_refresh`) calls `fetch_stock_act_disclosures` to warm the cache — but since the cache is in-memory and process-local, the scheduler process warms its own private cache that no web worker ever reads. The cache-warming jobs consume upstream API quota and produce zero user-facing benefit.

**Assessment: IMPLEMENT.** This is a direct logical consequence of U2 and adds specific evidence that the bug is actively burning upstream API budget. Gemini is correct. Fixing U2 (Redis migration) automatically resolves this, but it should be explicitly tested post-fix: verify that a cache write from the scheduler process is readable by a separate web worker process.

---

### UI-2 — Rate Limiter Memory Leak (Gemini only)
**What it is:** `_rate_limit_store` grows unboundedly as new IPs access the API. There is no TTL, no eviction, and no cleanup loop. In a long-running process, this will cause gradual memory exhaustion.

**Assessment: IMPLEMENT as part of U1.** The fix is identical to U1 (migrate to Redis with expiring keys). Calling this out separately ensures the memory leak is not treated as already-resolved by the multi-process fix alone — it must be confirmed that keys are set with `EXPIRE`.

---

### UI-3 — LLM Prompt Injection Defense is Regex-Only (Gemini only)
**What it is:** `_sanitize_event_summary()` (`panopticon.py:115–124`) uses a regex blocklist to prevent prompt injection before passing user-influenced content to the Anthropic LLM. Regex blocklists are trivially bypassed (Unicode substitutions, whitespace insertion, language variation). Generated LLM output is then displayed directly to other users, making this a stored prompt injection vector.

**Assessment: IMPLEMENT.** This is a legitimate P1 security finding. The fix requires a layered approach:
1. Move the primary defense to the **system prompt**: instruct the model to ignore any instructions embedded in the input data and to only perform its specified summarization task.
2. Add output validation: reject or flag any LLM response that contains instruction-like language (e.g., "ignore previous instructions", URLs, code blocks) before storing or rendering it.
3. Keep the input sanitizer as a defense-in-depth layer but do not rely on it as the primary control.

---

### UI-4 — Timing Side-Channel in Demo Mode (Grok only)
**What it is:** Grok noted that `get_demo_safe_data()` still calls `get_btc_price()` in demo mode, which means response timing varies based on whether a live upstream call is made. An attacker monitoring response times could potentially infer live data-fetching behavior.

**Assessment: INVESTIGATE FURTHER.** This is a low-probability, low-impact concern for the current threat model (public dashboard, not a financial execution system). The more important question is whether `get_btc_price()` is called with redacted output but a real network request, which wastes upstream quota in demo mode. Audit whether demo mode should short-circuit all live calls and return entirely static fixtures.

---

### UI-5 — Rate Limiter Key Collision on Aliased Routes (Gemini only)
**What it is:** The rate limiter key is `f"{ip}:{request.path}"` (`panopticon.py:44`). Routes with multiple aliases (e.g., `/api/panopticon/whale-alerts` and `/api/panopticon/whales`) receive independent rate-limit buckets for the same underlying resource, allowing a user to double their effective request rate by alternating between aliased paths.

**Assessment: IMPLEMENT.** The rate-limit key should be scoped to the logical resource (e.g., the view function name or a canonical path), not the raw URL string. When migrating to `Flask-Limiter`, use the decorator on the canonical route and ensure aliases share a key.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1 — Severity of Placeholder Date Issue
- **Gemini:** CRITICAL — treats it as a user trust failure and data integrity breach.
- **Grok:** HIGH — acknowledges it is misleading but notes the UI banner (`panopticon.html:990–992`) partially mitigates it.

**Tiebreaker ruling: Gemini is correct.** The UI banner is a mitigation for the *absence* of live data, not for the *presence of factually wrong data*. A user who sees a future-dated congressional disclosure on an "intelligence" dashboard will immediately distrust the entire platform, regardless of a banner. The banner says "data may be unavailable" — it does not say "the dates shown are impossible." This is a P0 fix, not P1.

---

### Conflict 2 — Severity of External API Rate Limiting
- **Grok (Cycle 2):** Rated the lack of hardcoded CoinGecko rate limit enforcement as HIGH (P1).
- **Gemini:** Did not independently escalate this beyond the U2 multi-worker issue.

**Tiebreaker ruling: Grok's framing is correct but subsumed by U2.** The root cause of the external API rate-limit risk is the non-shared cache, not the absence of a hardcoded limit value. Once U2 is fixed, N workers share one cache and the effective outbound call rate collapses. Add CoinGecko's documented limit (50 calls/minute on the free tier) as a code comment beside `_rate_limited_get` for documentation hygiene, but this does not require a separate structural fix.

---

## VALIDATED STRENGTHS (both models confirmed — do NOT change)

1. **Defensive Schema Parsing in `_extract_asset_from_hit`** (`panopticon_service.py:242–259`): Both models acknowledged this as a competent, intentional defense against API schema drift. The multi-key fallback plus `SCHEMA_DRIFT` logging is the right pattern for an undocumented endpoint. Do not simplify or remove this logic.

2. **Exponential Backoff in `_rate_limited_get`** (`panopticon_service.py:76–98`): Both models confirmed this is correctly implemented. The retry logic with backoff and the 0.5-second courtesy sleep are appropriate for a non-public API. Keep as-is; the Redis migration does not require changes here.

3. **Demo Mode Redaction Architecture** (`services/panopticon_service.py:1014–1038` + `core/blueprints/panopticon.py:79–104`): Both models assessed the demo mode data-redaction path as functionally secure. The separation between live and demo data is correctly gated. Do not refactor this path.

4. **Fallback Banner UI Component** (`templates/panopticon.html:989–993`): Both models noted this exists and correctly surfaces non-live data state to the user. The component is doing its job. Fix the data behind it (placeholder dates); do not remove or alter the banner itself.

5. **Batch Quality Warning for "See Filing" Results** (`panopticon_service.py:278–285`): Grok explicitly called this a "good detection mechanism." It is a proactive data quality sensor. Keep it.

---

## LAW COMPLIANCE CONSENSUS

| Legal Area | Status | Determination |
|---|---|---|
| STOCK Act / Congressional Disclosure | **Compliant (display)** | The feature displays public disclosure data; it does not generate, suppress, or modify it. No legal violation in scraping publicly posted government data. |
| Computer Fraud and Abuse Act (CFAA) | **Marginal risk** | Scraping `efts.house.gov` (a government server) without a documented API agreement is technically in a gray zone. There is no evidence of authorization denial, but the absence of a terms-of-service review is a legal gap. Recommend legal counsel review before public launch. |
| GDPR / CCPA | **Insufficient information** | The audit did not surface IP-address logging or user data retention policies. The rate limiter stores IPs in (currently in-memory, but soon Redis) state. Ensure IP data is not persisted beyond the rate-limit window TTL and that a privacy policy addresses this. |
| Financial Advice Regulations (SEC, FINRA) | **Risk present** | Displaying congressional trade data alongside LLM-generated summaries could be construed as investment analysis. A clear disclaimer ("This is not financial advice; this is public disclosure data") must be present on every rendered view. Neither model confirmed this disclaimer exists in the template. **Investigate.** |

---

## SECURITY CONSENSUS

Priority order of security findings both/all models raised:

1. **[CRITICAL] Multi-process rate limiter bypass** — Allows unlimited API abuse from any user with basic load-balanced request distribution. Directly exploitable. (U1)
2. **[HIGH] Prompt injection into LLM → stored XSS-adjacent output** — Gemini's UI-3 finding. User-influenced content reaches Anthropic API with only regex defense; output rendered to all users. (UI-3)
3. **[MEDIUM] IP data in Redis without explicit TTL/retention policy** — Post-U1 fix, IP addresses will be stored in Redis. Ensure EXPIRE is set on all rate-limit keys to comply with data minimization principles. (UI-2 consequence)
4. **[LOW] Demo mode timing side-channel** — Grok's UI-4. Low practical exploitability; investigate whether live calls should be fully suppressed in demo mode.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class intelligence product:

### Gap 1 — No Centralized Observability for Data Pipeline Health
Both models recommended monitoring/alerting for the `efts.house.gov` endpoint (U3) and the `SCHEMA_DRIFT` warning path. A world-class implementation would have a dedicated data pipeline health dashboard: green/yellow/red status for each upstream source (efts.house.gov, CoinGecko, mempool.space), with automated Slack/PagerDuty alerts on degradation. Currently there is no evidence this exists.

### Gap 2 — No Process-Safe State Management
Both models independently converged on the same architectural gap: the application was designed for single-process execution and has never been hardened for production multi-process deployment. A world-class platform running on Gunicorn would have Redis as a first-class infrastructure dependency from day one, not a retrofit.

### Gap 3 — Placeholder/Fallback Data Quality Assurance
Both models flagged that fallback data is not held to the same quality standard as live data. A world-class intelligence platform would maintain a curated, version-controlled set of golden sample records (real historical disclosures with verified dates, tickers, and amounts) that serve as both the fallback dataset and the integration test fixtures. This eliminates both the misleading-date problem and the risk of test fixtures diverging from real data structure.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Replace `_rate_limit_store` dict with Redis-backed `Flask-Limiter` | `core/blueprints/panopticon.py:29, 36–63` | both | Multi-worker bypass renders rate limiting non-functional; directly exploitable |
| **P0 CRITICAL** | Replace `_cache` dict with Redis + TTL via `Flask-Caching[redis]`; remove `_cache_lock` | `services/panopticon_service.py:35–72` | both | Non-shared cache multiplies upstream API calls by worker count; scheduler cache-warming is currently a no-op |
| **P0 CRITICAL** | Replace future-dated placeholder records with real, verifiable historical congressional disclosures | `services/panopticon_service.py:296–364` | both (Gemini CRITICAL, Grok HIGH) | Presenting future dates as historical data destroys product credibility; tiebreaker favors CRITICAL |
| **P1 HIGH** | Strengthen `_sanitize_event_summary` with system-prompt-level LLM defense + output validation | `core/blueprints/panopticon.py:115–124` | gemini | Regex blocklist is trivially bypassed; LLM output displayed to all users = stored prompt injection risk |
| **P1 HIGH** | Add external monitoring/alerting for `efts.house.gov` endpoint health and `SCHEMA_DRIFT` log spikes | `services/panopticon_service.py:193` | both | Undocumented endpoint is primary data source with no SLA; silent failures degrade product to placeholder-only mode with no notification |
| **P1 HIGH** | Verify and document Redis EXPIRE on all rate-limiter keys to prevent memory leak and ensure data minimization | `core/blueprints/panopticon.py:29` (post-fix) | gemini (unique, but consequence of P0) | Without TTL, IP store grows unboundedly; GDPR/CCPA data minimization also requires bounded retention |
| **P1 HIGH** | Add financial advice disclaimer to all Panopticon template views | `templates/panopticon.html` | synthesized from legal review | LLM summaries of congressional trades without disclaimer risks regulatory exposure |
| **P2 MEDIUM** | Fix rate-limiter key to use canonical resource name, not raw `request.path` | `core/blueprints/panopticon.py:44` | gemini | Aliased routes give users double the effective rate limit |
| **P2 MEDIUM** | Validate that post-Redis-migration, scheduler cache writes are readable by web worker processes | `services/scheduler.py:607` | gemini | Cache-warming was previously a no-op; must be explicitly verified post-fix |
| **P2 MEDIUM** | Refactor redundant dual-key caching between `fetch_disclosures` and `fetch_stock_act_disclosures` | `services/panopticon_service.py:182, 269` | gemini | Same data stored under two keys creates cache coherence risk |
| **P2 MEDIUM** | Audit demo mode to determine whether live upstream calls (`get_btc_price()`) should be suppressed entirely | `services/panopticon_service.py:1014–1038` | grok | Demo mode should not consume upstream API quota; investigate timing side-channel |
| **P2 MEDIUM** | Add `CFAA`/ToS legal review for efts.house.gov scraping prior to public launch | `services/panopticon_service.py:193` | synthesized | Government server scraping without authorization documentation is a legal gray zone |

---

## CYCLE 2 VERDICT

**This code is NOT production-ready.**

Two independent AI models reached full consensus on three separate architectural failures, any one of which would constitute a production incident within hours of deployment:

1. The rate limiter does not function in a multi-worker environment.
2. The cache does not function in a multi-worker environment.
3. The primary fallback dataset contains factually impossible data.

The first two failures share a single root cause — the entire state management layer was designed for single-process execution and has never been adapted for production deployment. This is not a bug in a corner case; it is a fundamental architectural assumption that is wrong for any real hosting environment.

The third failure is an independent data integrity issue that would immediately damage user trust in the product's most prominent intelligence claim.

**Absolute final blockers before any production deployment:**
- Redis must be a running infrastructure dependency.
- `_rate_limit_store` and `_cache` must be fully migrated to Redis.
- All placeholder records must use real historical dates.

The P1 items (LLM prompt injection, endpoint monitoring, financial disclaimer) are not launch blockers for a private beta but must be resolved before public launch.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/audits/panopticon_CONSENSUS_C2.md.

This is the FINAL PASS for panopticon.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Replace `_rate_limit_store` dict with Redis-backed Flask-Limiter | core/blueprints/panopticon.py:29,36–63 | models: both | Multi-worker bypass renders rate limiting non-functional
P0 CRITICAL | Replace `_cache` dict with Redis+TTL via Flask-Caching[redis]; remove _cache_lock | services/panopticon_service.py:35–72 | models: both | Non-shared cache multiplies upstream API calls; scheduler cache-warming is currently a no-op
P0 CRITICAL | Replace future-dated placeholder records with real verifiable historical congressional disclosures | services/panopticon_service.py:296–364 | models: both | Future dates presented as historical data destroys product credibility
P1 HIGH     | Strengthen _sanitize_event_summary with system-prompt LLM defense + output validation | core/blueprints/panopticon.py:115–124 | models: gemini | Regex blocklist bypassed; LLM output rendered to all users = stored prompt injection
P1 HIGH     | Add external monitoring/alerting for efts.house.gov endpoint health and SCHEMA_DRIFT log spike thresholds | services/panopticon_service.py:193 | models: both | Undocumented endpoint is primary data source; silent failure degrades to placeholder with no alert
P1 HIGH     | Ensure all Redis rate-limiter keys are set with EXPIRE (TTL) to prevent memory leak and satisfy data minimization | core/blueprints/panopticon.py:29 post-fix | models: gemini | Unbounded growth; GDPR/CCPA data minimization requires bounded retention
P

---

# WINNER DETERMINATION

# FINAL AUDIT VERDICT

## WINNER: **Gemini**

Gemini consistently demonstrated superior analytical depth across both cycles, correctly identifying the multi-process state vulnerability as an *architectural* flaw rather than merely a code-level bug, and uniquely surfaced the misleading future-dated placeholder data as a data integrity and user trust failure — a finding sharp enough that Grok explicitly credited it in Cycle 2 and the consensus engine upgraded the severity rating based on Gemini's rationale alone. Its recommendations were more specific, better cited, and more actionable than Grok's, and it caught issues that required a second pass from Grok to validate.

---

## SCORING BREAKDOWN

| Criterion | Gemini | Grok | GPT-4o |
|---|---|---|---|
| **Accuracy** — Cycle 1 findings validated in Cycle 2 | ✅ Strong — multi-process flaw, placeholder dates both confirmed | ✅ Adequate — confirmed same core findings | ❌ Did not complete |
| **Depth** — Issues others missed | ✅ Unique: future-dated placeholder = trust failure; upgraded consensus severity | ⚠️ Missed placeholder date issue until Gemini raised it | ❌ N/A |
| **Actionability** — Specific, implementable recommendations | ✅ Named specific libraries (Flask-Limiter + Redis), provided code examples | ⚠️ Identified problems clearly but recommendations were less prescriptive | ❌ N/A |
| **Completeness** — Full section coverage | ✅ Covered all five questions with line citations | ⚠️ Covered all sections but missed LLM prompt injection scoring | ❌ N/A |

---

## FINAL SECOND-PASS PRIORITY LIST

*Definitive ordered implementation sequence. Do not reorder — dependencies flow top to bottom.*

---

### 🔴 P0 — PRODUCTION BLOCKERS (Deploy nothing until resolved)

**P0-1 — Replace In-Memory Rate Limiter with Redis-Backed Flask-Limiter**
- **File:** `core/blueprints/panopticon.py:29, 36–63`
- **Why first:** Security bypass risk scales linearly with worker count. Every additional Gunicorn worker multiplies attacker advantage. This is the single highest-severity exploitable flaw.
- **Action:** Remove `_rate_limit_store` dict entirely. Install `Flask-Limiter`, configure `storage_uri="redis://localhost:6379"`, apply `@limiter.limit("60/minute")` to all panopticon routes.

**P0-2 — Replace In-Memory Cache with Redis-Backed Shared Cache**
- **File:** `services/panopticon_service.py:35–72`
- **Why second:** Without shared cache, every worker independently hammers `efts.house.gov`, multiplying upstream request volume by worker count. Given the undocumented API (see P1-1), this is the most direct path to an IP ban that takes the entire feature offline.
- **Action:** Replace `_cache` dict with `flask_caching` configured against Redis (`CACHE_TYPE="redis"`). Set TTL to match current in-memory TTL values.

---

### 🟠 P1 — HIGH SEVERITY (Must resolve before any user-facing traffic)

**P1-1 — Document and Monitor the Undocumented efts.house.gov Endpoint**
- **File:** `services/panopticon_service.py:193`
- **Why here:** `https://efts.house.gov/LATEST/search-index` is an internal frontend search endpoint, not a public API. It carries zero uptime or schema guarantees. P0-2 reduces hammering risk, but schema breakage remains a silent failure mode.
- **Action:** (a) Add a nightly canary request that validates response shape and alerts on schema drift. (b) Document the endpoint's assumed contract in a `THIRD_PARTY_APIS.md` file. (c) Set a hard circuit-breaker: if 3 consecutive requests fail schema validation, fall back gracefully and page on-call.

**P1-2 — Purge or Correct Future-Dated Placeholder Data**
- **File:** `services/panopticon_service.py:296–364` (`_generate_disclosure_placeholders`)
- **Why here:** Placeholder records dated in the future (e.g., "2025-09-15" from a 2026 system clock) will surface in an "intelligence" dashboard as apparently real disclosures. This is a data integrity failure that directly undermines the product's trust proposition — users making decisions on this data face active harm.
- **Action:** (a) Replace all hardcoded future dates with `datetime.utcnow().date()` or clearly labeled mock dates. (b) Add a prominent `[PLACEHOLDER — NOT REAL DATA]` flag to every generated record. (c) Add a unit test that asserts no placeholder date exceeds `datetime.utcnow()`.

**P1-3 — Harden LLM Prompt Injection Defense**
- **Severity:** HIGH (Gemini scored; Grok did not score — treat as single-model finding requiring verification)
- **Action:** Audit all user-supplied strings passed to LLM prompt templates. Wrap inputs in explicit delimiter blocks (e.g., `[USER INPUT START]...[USER INPUT END]`). Add an output validation layer that rejects responses containing instruction-like patterns before rendering.

---

### 🟡 P2 — MEDIUM SEVERITY (Resolve within first sprint post-launch)

**P2-1 — Strengthen Schema Fallback in `_extract_asset_from_hit`**
- **File:** `services/panopticon_service.py:242–259`
- **Why:** The final fallback — searching a full JSON dump for keywords — is O(n) on record size and produces false positives. This degrades data quality silently.
- **Action:** Replace keyword scan with a structured `SCHEMA_DRIFT` alert that increments a Prometheus counter and returns `None` rather than a guessed value. Treat `SCHEMA_DRIFT` alerts as a trigger to update the parser.

**P2-2 — Add Explicit Rate Limit Documentation for efts.house.gov**
- **File:** `services/panopticon_service.py:76–98`
- **Why:** The courtesy sleep (0.5s) and backoff are reasonable guesses against an undocumented endpoint. If the real limit is lower, the current implementation will cause bans; if higher, it's unnecessarily slow.
- **Action:** Instrument all outbound requests with latency and HTTP 429 metrics. If 429s appear, back off aggressively and alert. Document the assumed limits in code comments with a "last validated" date.

---

### 🟢 P3 — LOW SEVERITY / HYGIENE (Resolve before v1.1)

**P3-1 — Add Integration Tests for Multi-Worker Behavior**
- Spin up a 2-worker test instance. Assert that a single user cannot exceed the rate limit across workers. Assert that cache is shared. These tests would have caught P0-1 and P0-2 at development time.

**P3-2 — Batch Warning Threshold Tuning**
- **File:** `services/panopticon_service.py:278–285`
- The 80% "See filing" batch warning threshold is arbitrary. Instrument it, observe real production distributions, and set the threshold based on empirical data.

---

*End of audit. Overall production readiness remains 3.5/10. Do not deploy until P0-1 and P0-2 are resolved and verified under load.*