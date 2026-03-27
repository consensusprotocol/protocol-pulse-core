# CONSENSUS REPORT — PANOPTICON — CYCLE 2
Generated: 2026-03-26 06:21
Models: gemini, grok (+1 failed: gpt4o — token limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| API Rate Limiting | CRITICAL | N/A | CRITICAL | **CRITICAL** |
| Cache Architecture | CRITICAL | N/A | CRITICAL | **CRITICAL** |
| Scheduler Cache Invalidation | CRITICAL | N/A | (not scored) | **CRITICAL** |
| Congressional Data Fetching | HIGH | N/A | HIGH | **HIGH** |
| Fallback Data Transparency | HIGH | N/A | MEDIUM-HIGH | **HIGH** |
| Brand / Law Compliance | MEDIUM | N/A | MEDIUM | **MEDIUM** |
| API Schema Validation | MEDIUM | N/A | MEDIUM | **MEDIUM** |
| Circuit Breaker / Upstream Failure | (not scored) | N/A | HIGH | **HIGH** |
| Demo Mode Data Leak | (not scored) | N/A | MEDIUM | **INVESTIGATE** |
| Anthropic API Timeout/Retry | (not scored) | N/A | MEDIUM | **MEDIUM** |

*GPT-4o failed due to TPM rate limit (57,273 tokens requested vs. 30,000 limit). Consensus is derived from 2 models only. Confidence is slightly reduced on non-unanimous items, noted where relevant.*

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### U1 — API Rate Limiting Is Non-Functional
**Both models rated this CRITICAL.**

- **What it is:** Flask-Limiter is initialized in `core/blueprints/panopticon.py` (lines 27–63), creating the full infrastructure for rate limiting. However, no `@limiter.limit()` or `@_get_limiter().limit()` decorators are applied to any API route handler (e.g., `/api/panopticon/disclosures` at line 181, `/api/panopticon/whale-alerts` at line 203, and all subsequent API routes through line 316). The protection mechanism exists but is never activated.
- **File/Line:** `core/blueprints/panopticon.py`, lines 181, 203, 233, and all API route definitions through ~line 316.
- **What to change:** Apply rate limit decorators to every API endpoint. Use tiered limits based on endpoint cost. Example:
  ```python
  @panopticon_bp.route('/api/panopticon/disclosures')
  @_get_limiter().limit("20 per minute; 200 per hour")
  def api_disclosures():
      ...

  @panopticon_bp.route('/api/panopticon/whale-alerts')
  @_get_limiter().limit("30 per minute")
  def api_whale_alerts():
      ...
  ```

### U2 — In-Memory Cache Is Unfit for Production
**Both models rated this CRITICAL.**

- **What it is:** `SimpleCache` is used as the caching backend (`services/panopticon_service.py`, line 52). This is a process-local cache. In any production deployment using multiple Gunicorn workers (the standard), each worker maintains its own isolated cache. This causes: (a) cache stampedes where every worker independently calls upstream APIs simultaneously; (b) the 30-minute TTL being violated routinely; (c) potential upstream rate limit violations from the burst of redundant calls; and (d) inconsistent data served to users depending on which worker handles their request. The code comments on lines 37–38 acknowledge Redis is needed for production — this self-documented gap was never closed.
- **File/Line:** `services/panopticon_service.py`, lines 34–120, particularly line 52.
- **What to change:** Replace `SimpleCache` with a Redis-backed Flask-Caching instance for all production deployments:
  ```python
  # services/panopticon_service.py
  cache_config = {
      "CACHE_TYPE": "RedisCache",
      "CACHE_REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
      "CACHE_DEFAULT_TIMEOUT": 1800,
  }
  ```
  Add `REDIS_URL` to environment configuration and deployment documentation. Ensure staging environment mirrors production in this regard.

### U3 — Undocumented efts.house.gov Endpoint Used for Health Check
**Both models rated this HIGH.**

- **What it is:** The `check_efts_health` function (`services/panopticon_service.py`, lines 1407–1441) queries `https://efts.house.gov/LATEST/search-index` — an endpoint explicitly described in the code comments (line 1408) as undocumented. The function is used to determine whether the system should enter fallback mode, making its reliability load-bearing for the user experience. Undocumented government API endpoints are changed or removed without notice, with no deprecation cycle.
- **File/Line:** `services/panopticon_service.py`, lines 1407–1441, specifically line 1414.
- **What to change:** Replace with a stable, documented check. A HEAD request to the House Disclosure portal's main page is sufficient to determine connectivity:
  ```python
  response = requests.head(
      "https://disclosures-clerk.house.gov/",
      timeout=5,
      headers={"User-Agent": HEADERS["User-Agent"]}
  )
  return response.status_code < 500
  ```

### U4 — Fallback Data Not Clearly Labeled as Historical
**Both models flagged this (HIGH / MEDIUM-HIGH).**

- **What it is:** When live data is unavailable, `_generate_disclosure_placeholders` (lines 436–642 in `services/panopticon_service.py`) returns historical verified filings. These are merged with live data in the response (lines 423–431). The existing banner in `templates/panopticon.html` (lines 1294–1297) indicates data is "temporarily unavailable" but does not communicate that what is being shown is a curated static historical dataset. Users may believe they are viewing recent disclosures.
- **File/Line:** `templates/panopticon.html`, lines 1294–1297.
- **What to change:** Update banner text to be explicit:
  ```html
  <!-- BEFORE -->
  <div class="fallback-banner">Live data temporarily unavailable</div>

  <!-- AFTER -->
  <div class="fallback-banner">
    ⚠ Live feed unavailable — displaying a static set of verified historical
    disclosures for reference. Data may not reflect recent filings.
    <a href="#" class="retry-link">Retry live connection</a>
  </div>
  ```

---

## MAJORITY FINDINGS (2 of 2 models agree)

*Note: With only 2 functional models, "majority" and "unanimous" overlap. Items listed here were noted with different emphasis or framing by each model but represent shared concerns.*

### M1 — QuiverQuant Response Has No Schema Validation
- **What it is:** The JSON response from QuiverQuant is parsed with only a type check (`isinstance(resp, list)`, line 321 in `services/panopticon_service.py`). Field names like `Ticker` and `TransactionDate` (lines 325–349) are accessed directly. If QuiverQuant renames fields, adds null values, or restructures the response, the code will fail silently or produce corrupt data.
- **File/Line:** `services/panopticon_service.py`, lines 319–349.
- **Recommendation:** Implement `pydantic` schema validation:
  ```python
  from pydantic import BaseModel, validator
  from typing import Optional

  class QuiverDisclosure(BaseModel):
      Ticker: str
      TransactionDate: str
      Representative: Optional[str] = "Unknown"
      Transaction: Optional[str] = "Unknown"
      Range: Optional[str] = "$1K - $15K"

      @validator('Ticker')
      def ticker_must_not_be_empty(cls, v):
          assert v and v.strip(), "Ticker cannot be empty"
          return v.upper()
  ```

### M2 — Brand Palette CSS Violations
- **What it is:** `templates/panopticon.html` defines CSS variables that violate Governing Law 1. Specifically: `--pn-bg: #000` (line 15) uses pure black, which is explicitly prohibited; `--pn-red: #ff3b5f` (line 23) uses an incorrect red that deviates from the mandated `#CC2222`.
- **File/Line:** `templates/panopticon.html`, lines 15 and 23.
- **What to change:**
  ```css
  :root {
      --pn-bg: #0A0A0F;     /* FIX: was #000 — pure black prohibited */
      --pn-red: #CC2222;    /* FIX: was #ff3b5f — wrong brand red */
      --pn-red-dim: rgba(204, 34, 34, 0.12); /* update derived value */
  }
  ```

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X1 — Scheduler Cache Invalidation Is Completely Broken (Gemini — CRITICAL)
**Assessment: IMPLEMENT IMMEDIATELY**

This is the most significant new finding from Cycle 2. Gemini identified that `services/scheduler.py` (lines 607–637) attempts to proactively refresh cached data by importing and manipulating `_cache` from `panopticon_service`. However, `panopticon_service.py` exports no variable named `_cache` — the fallback dictionary is named `_cache_dict` (line 69). This causes an `ImportError`. Furthermore, even if the name were corrected, the scheduler would be manipulating the dictionary fallback while the application uses the Flask-Caching `SimpleCache` instance — a completely separate object. The scheduled refresh tasks are entirely non-functional. Data only refreshes when TTL expires organically. The scheduler cron jobs exist and appear to run, but they accomplish nothing. This is a silent failure that will be invisible in logs unless the `ImportError` is surfaced.

**Fix:**
```python
# services/scheduler.py — refactor refresh tasks to use
# the Flask-Caching instance directly via the app context
from flask import current_app

def panopticon_congress_refresh():
    with app.app_context():
        cache = current_app.extensions['cache']  # Flask-Caching instance
        cache.delete('panopticon_stock_act')
        fetch_stock_act_disclosures(force_refresh=True)
```

### X2 — Circuit Breaker Lacks Active Response (Grok — HIGH)
**Assessment: IMPLEMENT**

Grok identified that the `_EFTS_FAIL_COUNT` circuit breaker (`services/panopticon_service.py`, line 1403) increments a failure counter and logs errors after `_EFTS_CIRCUIT_BREAKER_THRESHOLD` failures (line 1405), but takes no active action: no admin notification, no automatic disabling of the health check, no status flag visible to the monitoring layer. The system continues hammering a failing endpoint. Add a flag that actively short-circuits subsequent health check calls after threshold is breached, and integrate with whatever alerting system is in use.

**Fix:**
```python
_EFTS_CIRCUIT_OPEN = False  # Add module-level flag

def check_efts_health():
    global _EFTS_FAIL_COUNT, _EFTS_CIRCUIT_OPEN
    if _EFTS_CIRCUIT_OPEN:
        logger.warning("EFTS circuit breaker OPEN — skipping health check")
        return False
    # ... existing logic ...
    if _EFTS_FAIL_COUNT >= _EFTS_CIRCUIT_BREAKER_THRESHOLD:
        _EFTS_CIRCUIT_OPEN = True
        # TODO: send admin alert here
```

### X3 — Live BTC Price Leaked in Demo Mode (Grok — MEDIUM)
**Assessment: INVESTIGATE**

Grok observed that `btc_price` in `core/blueprints/panopticon.py` (line 80) is populated with real data from `get_btc_price()` even when serving the demo/free-tier response. The intent appears to be full redaction for non-Commander users, but `btc_price` is included as live data. This is a minor inconsistency — BTC price is public information — but it violates the stated design intent and could set a precedent for similar leaks in other fields. Investigate whether this is intentional (BTC price used as a hook to show value) or an oversight. If the latter, redact or replace with a static value.

### X4 — Anthropic API Has No Timeout or Retry Logic (Grok — MEDIUM)
**Assessment: IMPLEMENT**

`get_make_bitcoin_case` (`services/panopticon_service.py`, lines 1346–1389) calls the Anthropic API without explicit timeout or retry configuration. If Anthropic's API is slow or returns a 5xx, the function will hang for the default `httpx` timeout (which may be very long or None) and not retry. This directly degrades the user experience on the dashboard's AI commentary feature.

**Fix:**
```python
response = anthropic_client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    timeout=15.0,  # Add explicit timeout
    messages=[{"role": "user", "content": prompt}],
)
```
Wrap with retry logic using `tenacity` or a simple `try/except` with one retry.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1: Severity of Fallback Data Transparency Issue
- **Gemini:** HIGH — users may be significantly misled by unlabeled historical data.
- **Grok:** MEDIUM-HIGH — the existing banner provides partial mitigation; risk is real but not catastrophic.
- **Tiebreaker: Gemini is correct.** The existing banner says data is "temporarily unavailable," which implies the underlying data is current-but-unreachable. Showing historical data under that label is materially misleading. Users making decisions based on what they believe are recent congressional disclosures, when they are actually viewing 12-month-old filings, is a trust and potential accuracy issue. Rate this HIGH and fix it at P1.

### Conflict 2: Brand Palette Urgency
- **Gemini:** Implied must-fix before deployment (included in compliance violations section).
- **Grok:** Agreed it needs fixing but suggested it could be post-launch if critical issues take precedence.
- **Tiebreaker: Grok is correct on urgency, Gemini is correct on the bug.** The palette violation is real and must be fixed, but it does not block deployment in the same way that unthrottled API endpoints or broken cache invalidation do. Classify as P2 — fix in the same pass but do not gate deployment on it if timelines are tight.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

1. **Fallback System Existence:** Both models validated that the decision to implement `_generate_disclosure_placeholders` (lines 436–642) is architecturally sound. Having a rich fallback that prevents empty dashboards is the right call. The system design is good; only the labeling needs improvement.
2. **Exponential Backoff on Rate Limits:** The `_rate_limited_get` wrapper (lines 123–146) with exponential backoff on 429 responses is correctly implemented and the right approach for upstream API calls.
3. **QuiverQuant as Primary Source:** Both models agreed that using QuiverQuant rather than scraping `efts.house.gov` directly is a sound architectural decision. It offloads rate limit management and schema maintenance to a specialized third party.
4. **Demo Mode / Tiered Access Gate:** The redaction logic for non-Commander users (`core/blueprints/panopticon.py`, lines 79–103) is structurally sound. The concept is correct; only the BTC price edge case (X3) is worth investigating.
5. **Health Check Circuit Breaker Concept:** Both models acknowledged that having `_EFTS_FAIL_COUNT` and a threshold is the right pattern. The implementation needs improvement (X2), but the design intent is validated.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Detail |
|---|---|---|
| LAW 1 — Brand Palette | **VIOLATED** | `--pn-bg: #000` (pure black prohibited); `--pn-red: #ff3b5f` (must be `#CC2222`). File: `templates/panopticon.html`, lines 15, 23. |
| LAW 2 — Typography | **UNREVIEWED** — GPT-4o unavailable | No definitive finding; neither model flagged violations. |
| LAW 3 — Component Standards | **UNREVIEWED** — GPT-4o unavailable | No definitive finding. |
| Other Laws | **UNREVIEWED** — GPT-4o unavailable | With only 2 of 3 models available, Law compliance coverage is incomplete. A targeted CSS/HTML pass against the full Visual Design System is recommended before final deployment. |

**Determination:** LAW 1 is definitively violated. Full law compliance cannot be confirmed without GPT-4o's coverage. The second pass prompt should explicitly include a CSS compliance review.

---

## SECURITY CONSENSUS

Priority order of security issues flagged by both/all available models:

1. **[CRITICAL] Unthrottled API Endpoints** — No rate limiting on any API route. Direct DoS vector. Attackers can also use the endpoints to exhaust all upstream API quotas (QuiverQuant, CoinGecko, Anthropic) within minutes, causing complete service degradation. Both models flagged.

2. **[HIGH] Upstream API Quota Exhaustion via Cache Miss** — With broken scheduler invalidation and process-local SimpleCache, each Gunicorn worker will independently exhaust upstream rate limits. This is a reliability issue with security implications (service availability). Both models flagged.

3. **[MEDIUM] Undocumented Endpoint Dependency** — Reliance on undocumented government API creates potential for supply-chain-style disruption if the endpoint is repurposed, monitored, or blocked. Both models flagged.

4. **[MEDIUM] Demo Mode Data Boundary** — Possible unintentional data exposure in free-tier responses (BTC price). Grok only.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models that separate this from a truly world-class implementation:

1. **No production-grade shared cache (both models):** A world-class real-time intelligence dashboard cannot use a process-local in-memory cache. Redis with appropriate TTL strategies, cache warming on startup, and cache-aside patterns is the minimum bar.

2. **No API rate limiting enforcement (both models):** A world-class product protects its upstream API budget and its own infrastructure. The absence of any enforced rate limits is not just a security gap — it signals the feature was never production-hardened.

3. **Silent failure modes throughout (both models):** The broken scheduler, the non-functional circuit breaker, the ImportError in cache invalidation — these all fail silently. A world-class system emits structured alerts, updates a health dashboard, and pages on-call when critical subsystems malfunction. None of this exists.

4. **No schema validation on upstream APIs (both models):** Third-party APIs change. A world-class integration validates the contract on every response and fails loudly when the contract breaks, rather than silently producing corrupt data.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Apply `@_get_limiter().limit()` decorators to ALL API route handlers | `core/blueprints/panopticon.py:181, 203, 233` and all subsequent API routes | Both | Direct DoS vector; upstream API quota exhaustion; system is completely unprotected |
| **P0 CRITICAL** | Replace `SimpleCache` with Redis-backed Flask-Caching for production | `services/panopticon_service.py:52` | Both | Multi-worker cache stampedes; redundant upstream calls; service degradation under load |
| **P0 CRITICAL** | Fix scheduler cache invalidation — correct import name and target correct cache instance | `services/scheduler.py:607–637` | Gemini (unique, confirmed critical) | ImportError causes silent failure; scheduled refresh tasks are entirely non-functional |
| **P1 HIGH** | Replace undocumented `efts.house.gov/LATEST/search-index` health check with stable HEAD request | `services/panopticon_service.py:1407–1441, line 1414` | Both | Undocumented endpoint can change without notice; health check produces unreliable signals |
| **P1 HIGH** | Update fallback data banner to explicitly state data is historical, not live | `templates/panopticon.html:1294–1297` | Both | Users may make decisions based on data they believe is recent; trust and accuracy risk |
| **P1 HIGH** | Add active response to circuit breaker (set open flag, alert admin) | `services/panopticon_service.py:1403–1405` | Grok (unique, validated) | Counter increments but system continues hammering failing endpoint; no operator notification |
| **P1 HIGH** | Add explicit timeout and retry logic to Anthropic API call | `services/panopticon_service.py:1346–1389` | Grok (unique, validated) | Hanging requests degrade dashboard UX; no retry on transient 5xx |
| **P2 MEDIUM** | Fix CSS variable brand palette violations | `templates/panopticon.html:15, 23` | Both | LAW 1 violation; `--pn-bg:#000` and `--pn-red:#ff3b5f` both incorrect |
| **P2 MEDIUM** | Implement `pydantic` schema validation on QuiverQuant API response | `services/panopticon_service.py:319–349` | Both | Silent failures or corrupt data if upstream changes field names or structure |
| **P2 MEDIUM** | Investigate and resolve BTC price exposure in demo mode | `core/blueprints/panopticon.py:80` | Grok (unique) | May be intentional but violates stated redaction design intent; needs explicit decision |

---

## CYCLE 2 VERDICT

**Production Ready: NO**

This code has three P0 blockers that must be resolved before any production deployment:

1. **Zero API rate limiting** — the protection infrastructure exists but was never wired up. This is a single-line-per-route fix with outsized impact.
2. **Process-local cache in a multi-worker environment** — this is a known, self-documented issue in the codebase that was never resolved. It will cause service degradation immediately upon multi-worker deployment.
3. **Broken scheduler cache invalidation** — a silent `ImportError` means the entire proactive refresh system is non-operational. This is particularly insidious because the system *appears* to have scheduled refresh capability.

**Confidence note:** With GPT-4o unavailable, this consensus is based on 2 of 3 models. The findings on P0 items are high-confidence because both available models independently identified them. Law compliance coverage is incomplete and a full CSS audit pass against `VISUAL_DESIGN_SYSTEM.md` is warranted. If GPT-4o becomes available, a targeted Cycle 3 review of the template layer and law compliance is recommended.

The architectural bones are sound — the fallback system, the QuiverQuant integration choice, the circuit breaker concept, and the tiered access model are all correct decisions. The gaps are in hardening, not in design. Estimated remediation: 1–2 focused engineering sessions.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/audits/panopticon_CONSENSUS_C2.md.

This is the FINAL PASS for panopticon.
The first build was reviewed by 2 independent AI models (Gemini 2.5 Pro, Grok-3)
across 2 cycles. Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

---

# WINNER DETERMINATION

## WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles. In Cycle 1, it proactively cross-referenced Governing Laws before addressing the five questions — catching the brand palette violation that both other models missed entirely — while simultaneously identifying the two most critical architectural flaws (non-functional rate limiting, process-local cache) with precise file/line citations. In Cycle 2, it demonstrated intellectual honesty by explicitly naming what it missed and why, provided the most concrete user-transparency fix (specific banner text language), and its Cycle 1 findings were validated unanimously by the consensus report, confirming the highest accuracy rate of any single model.

**Runner-up: Grok** — Strongest on circuit breaker / upstream failure handling and the Demo Mode data leak, which Gemini missed entirely and which earned an "INVESTIGATE" flag in consensus. Grok's `pydantic` schema validation suggestion was more actionable than Gemini's generic recommendation.

**GPT-4o: Disqualified** — Token limit failure; no scoreable output in either cycle.

---

## FINAL SECOND-PASS PRIORITY LIST

Definitive ordered implementation list, synthesized from both cycles, all models, and the consensus report. Items marked 🔴 CRITICAL must block any production deployment.

---

### 🔴 TIER 1 — PRODUCTION BLOCKERS (Implement before any deployment)

**1. [U1] Apply Rate Limit Decorators to All API Routes**
- **File:** `core/blueprints/panopticon.py`, lines 181, 203, 233, and all API routes through ~line 316
- **Action:** Apply `@limiter.limit()` decorators with tiered limits by endpoint cost. High-cost endpoints (AI analysis, whale alerts) get tighter limits than low-cost status endpoints. The infrastructure already exists — it is simply never activated.
- **Why first:** Every API endpoint is currently completely unprotected. A single malicious or misconfigured client can exhaust all upstream API quotas (QuiverQuant, Anthropic) in seconds, taking down the entire service.

**2. [U2] Replace Process-Local Cache with Distributed Cache**
- **File:** `services/panopticon_service.py`, lines 34–120
- **Action:** Replace `SimpleCache` with Redis (via `flask-caching` with `RedisCache` backend). All cache keys, TTLs, and invalidation logic already exist — only the backend needs to swap. Add a `CACHE_TYPE=redis` config path with a `SimpleCache` fallback for local dev only.
- **Why second:** In any multi-worker deployment (gunicorn, uvicorn, k8s), each worker maintains an independent cache. Every worker misses every other worker's cached data, multiplying upstream API calls by the worker count and defeating all rate-limit budgeting.

**3. [U3] Fix Scheduler Cache Invalidation**
- **File:** Scheduler registration code (consensus-flagged CRITICAL, Gemini primary finding)
- **Action:** Ensure the background scheduler invalidates the shared cache (Redis after fix #2), not a process-local reference. Verify the scheduler runs in exactly one worker process, not one per worker. Use a distributed lock (Redis `SET NX`) to enforce single-scheduler execution.
- **Why third:** A scheduler that invalidates a local cache nobody else reads, or that runs N times across N workers, produces either stale data for all users or N× the upstream API call volume.

---

### 🟠 TIER 2 — HIGH SEVERITY (Implement within first sprint post-launch)

**4. [H1] Congressional Data Fetching — Undocumented Endpoint Risk**
- **File:** `services/panopticon_service.py`, lines 1414–1415
- **Action:** Replace the undocumented `efts.house.gov/LATEST/search-index?q=bitcoin&page[size]=1` health check with the officially documented House Disclosure search endpoint. Document the chosen endpoint's rate limits explicitly in code comments. Add a circuit breaker (see item #6) around this call.
- **Why:** The health check currently validates system status against an endpoint that can change schema or disappear without notice, producing false-healthy status readings.

**5. [H2] Fallback Data Transparency — User-Facing Banner**
- **File:** `templates/panopticon.html`, line 1295
- **Action:** Replace the current fallback banner with explicit language: *"LIVE DATA UNAVAILABLE — Displaying a static set of verified historical examples. Figures do not reflect current positions."* Add a timestamp of when the fallback was activated. Color-code the banner distinctly from the live-data state (use `--pn-gold` warning color, not the standard surface color).
- **Why:** Users currently cannot distinguish live data from historical fallback data. In a financial intelligence dashboard, this is a material transparency failure and a potential regulatory liability.

**6. [H3] Circuit Breaker for All Upstream API Calls**
- **File:** `services/panopticon_service.py`, all external HTTP call sites
- **Action:** Wrap QuiverQuant, `efts.house.gov`, and Anthropic API calls with a circuit breaker pattern (use `pybreaker` or implement manually with Redis state). After N consecutive failures, open the circuit, serve cached/fallback data immediately, and retry on a backoff schedule rather than hammering a failing upstream.
- **Why:** Currently, upstream failures cause cascading timeouts on every user request. The fallback exists but is only reached after full timeout exhaustion, degrading UX and wasting resources.

**7. [H4] Add Schema Validation on All External API Responses**
- **File:** `services/panopticon_service.py`, QuiverQuant response parsing (~line 319)
- **Action:** Define `pydantic` models for QuiverQuant disclosure responses and Anthropic API responses. Validate on ingest. On `ValidationError`, log the full raw response at WARNING level and route to fallback — do not propagate a `KeyError` or `TypeError` to the user.
- **Why (Grok's specific recommendation validated):** Schema changes from external APIs are silent failures under the current implementation. `pydantic` makes the contract explicit and failures observable.

---

### 🟡 TIER 3 — MEDIUM SEVERITY (Implement within first two sprints)

**8. [M1] Brand Palette Compliance — CSS Variables**
- **File:** `templates/panopticon.html`, lines 15–27
- **Action:**
  ```css
  --pn-bg: #0A0A0F;   /* was #000 — violates "never pure black" */
  --pn-red: #CC2222;  /* was #ff3b5f — violates Primary Red spec */
  --pn-red-dim: rgba(204, 34, 34, 0.12); /* adjust to match */
  ```
- **Why:** Violates LAW 1 of Governing Laws. Pure black backgrounds and off-spec reds will cause visual inconsistency if any shared component library or future template references the canonical palette.

**9. [M2] Demo Mode Data Leak Investigation**
- **File:** Flagged by Grok, consensus status: INVESTIGATE
- **Action:** Audit all routes for conditional logic gated on a `demo_mode` flag. Verify that demo mode cannot be activated by a client-supplied parameter (query string, cookie, header). Ensure demo data cannot be served to authenticated non-demo users due to a flag precedence bug.
- **Why:** Grok flagged this; Gemini did not assess it. Until audited, the risk level is unknown. If demo data can be triggered by a client parameter, it is a data integrity vulnerability.

**10. [M3] Anthropic API Timeout and Retry Hardening**
- **File:** `services/panopticon_service.py`, Anthropic API call sites
- **Action:** Set an explicit `timeout` on all `anthropic` client calls (recommend 30s max). Add a retry wrapper with exponential backoff (max 2 retries) specifically for 529 (overloaded) responses. Do not retry on 4xx errors. Log token usage per call to monitor quota burn rate.
- **Why:** Anthropic's API has variable latency and overload responses. Without an explicit timeout, a slow Anthropic response holds a worker thread indefinitely, compounding under the multi-worker cache problem identified in item #2.

**