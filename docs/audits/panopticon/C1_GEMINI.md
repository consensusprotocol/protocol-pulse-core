# PROTOCOL PULSE — CODE AUDIT: PANOPTICON

**AUDITOR:** Gemini 2.5 Pro
**DATE:** 2026-03-26 01:15 UTC

This report contains a detailed analysis of the `panopticon` feature, focusing on architecture, security, logic, and scalability as requested.

---

### Q1 — CONGRESSIONAL DATA FETCHING ARCHITECTURE

Is the efts.house.gov API integration correct and production-safe?

**DETAILED ANALYSIS**
The integration with `efts.house.gov` is functional but extremely brittle and contains a significant data integrity issue in its fallback mechanism.

1.  **Endpoint and Parameters:** The code targets `https://efts.house.gov/LATEST/search-index` (`panopticon_service.py:193`). This appears to be an internal search endpoint for the website's front end, not a documented public API. While the parameters (`q`, `dateRange`, etc.) seem to work, they are subject to unannounced changes at any time, which could break the service without warning.

2.  **Rate Limits:** The code correctly uses the `_rate_limited_get` wrapper and adds a courtesy sleep (`panopticon_service.py:223`). However, since this is not a public API, there are no documented rate limits. The current implementation is a reasonable guess but could still be too aggressive, leading to IP bans.

3.  **Schema Robustness:** The parsing logic is highly defensive, indicating the developer is aware of schema instability.
    *   `panopticon_service.py:205-212`: The code attempts to get data from multiple possible keys (e.g., `filing_name`, `name`, `display_names`). This is a sign of a fragile, undocumented API.
    *   `panopticon_service.py:242-259`: The `_extract_asset_from_hit` function is an explicit admission of this fragility. It tries several known-good keys and then logs a `SCHEMA_DRIFT` warning. The final fallback of searching a JSON dump of the entire record for keywords is clever but inefficient and prone to false positives.

4.  **Fallback System:** The fallback system (`_generate_disclosure_placeholders` at `panopticon_service.py:296`) is **not appropriate**. It uses hardcoded **future dates** (e.g., "2025-09-15", "2025-10-01" from the perspective of the 2026 generation date) for filings. The comment on line 297 states this is to "avoid misleading freshness," but presenting future events as historical data is fundamentally misleading and damages the credibility of the entire platform. While the UI displays a banner (`panopticon.html:989-993`), the data itself is nonsensical.

**SEVERITY:** HIGH

**SPECIFIC FIX**
1.  Acknowledge in documentation and monitoring that this endpoint is unstable and subject to break.
2.  **Most importantly, fix the placeholder dates.** They must be replaced with plausible, historical dates from real, publicly documented filings. The goal of a fallback is to show a realistic example of the data, not to present impossible data.

```python
# services/panopticon_service.py - SUGGESTED CHANGE

# In _generate_disclosure_placeholders(), change future dates to historical ones.
# Example for the first entry:
        {
            "entity": "Rep. Michael McCaul (R-TX)",
            "asset": "Bitcoin ETF (IBIT)",
            "trade_type": "purchase",
            "amount_range": "$15,001–$50,000",
            "chamber": "house",
            "party": "R",
            # CHANGE THESE DATES to be in the past.
            "date_filed": "2024-03-15",
            "date_traded": "2024-02-20",
            "days_to_file": 24,
            # ... rest of the placeholder data
        },
```

---

### Q2 — API RATE LIMITING

Are all API endpoints properly rate-limited?

**DETAILED ANALYSIS**
Rate limiting is implemented at both the incoming request level and outgoing external call level, but the incoming request limiter has a critical flaw for a production environment.

1.  **Blueprint Routes:** `core/blueprints/panopticon.py:36-64` implements an IP-based rate limiter (`_enforce_rate_limit`) applied to all `/api/panopticon/*` routes. This is the correct approach. It even correctly applies a tighter limit for the more expensive whale alerts endpoint.
2.  **CRITICAL FLAW:** The rate limiting store (`_rate_limit_store` on line 29) is a simple Python dictionary. In a production environment using a WSGI server like Gunicorn with multiple worker processes, **each worker will have its own separate, in-memory copy of this dictionary.** This completely defeats the purpose of the rate limit, as a user can simply round-robin requests across workers to bypass the limit. A user could easily exceed the intended 30 reqs/min by hitting 4 different workers 30 times each, for a total of 120 reqs/min.
3.  **External API Calls:** The `_rate_limited_get` function (`panopticon_service.py:76-98`) is well-designed. It implements exponential backoff with jitter for `429 Too Many Requests` responses and other request failures. This correctly respects upstream API limits for services like CoinGecko, mempool.space, etc.
4.  **Malicious User Risk:** Yes, due to the in-memory rate limiter flaw, a malicious user *can* trigger expensive upstream calls by hammering endpoints, with each request being handled by a different worker process. This could exhaust our upstream API quotas or get our server IP-banned.
5.  **Cache Sufficiency:** The same in-memory issue applies to the cache (`_cache` in `panopticon_service.py:35`). It is not shared between processes. A distributed cache like Redis is essential for this to be effective under load.

**SEVERITY:** CRITICAL

**SPECIFIC FIX**
Replace the in-memory dictionary for rate limiting and caching with a centralized store like Redis. The `Flask-Limiter` extension is a production-ready solution for the rate limiting part.

```python
# core/blueprints/panopticon.py - CONCEPTUAL FIX

# 1. In your app factory, initialize Flask-Limiter with a Redis store:
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
#
# limiter = Limiter(
#     get_remote_address,
#     app=app,
#     storage_uri="redis://localhost:6379"
# )

# 2. Apply the limiter to the blueprint routes instead of the custom implementation.
# Remove the _rate_limit_store and _enforce_rate_limit function.

from flask import Blueprint, jsonify
from app import limiter # Assuming limiter is initialized in app factory

panopticon_bp = Blueprint("panopticon", __name__)

@panopticon_bp.route("/api/panopticon/disclosures")
@limiter.limit("30/minute")
def api_disclosures():
    # ...

@panopticon_bp.route("/api/panopticon/whale-alerts")
@limiter.limit("10/minute") # Tighter limit
def api_whale_alerts():
    # ...

# services/panopticon_service.py should be refactored to use a Redis cache.
```

---

### Q3 — CLASSIFIED OVERLAY SECURITY

Is the Commander-gated CLASSIFIED overlay secure against client-side bypass?

**DETAILED ANALYSIS**
Yes, the security model is robust and correctly implemented. It is not vulnerable to client-side bypass.

1.  **Server-Side Data Withholding (Page):** The primary page route (`/panopticon` in `panopticon.py:130`) makes a clear server-side decision. On line 135, `demo_mode` is set based on the user's authentication status. If `demo_mode` is true, a completely separate, redacted data structure (`_DEMO_DATA` on line 139) is passed to the template. The real data from `get_dashboard_data()` is never fetched or sent to a free-tier user's browser.
2.  **Client-Side Appearance:** In `panopticon.html`, a user could inspect the DOM and remove the `pn-demo-overlay` div (`panopticon.html:982`). However, the data they would uncover is the hardcoded, redacted `_DEMO_DATA` (e.g., `{"entity": "██████████", ...}`), not the sensitive Commander-tier data.
3.  **API Route Guards:** All API endpoints (`/api/panopticon/*`) have a guard clause at the very beginning (e.g., `panopticon.py:164`, `panopticon.py:186`). These clauses check `_is_commander()` and immediately return a `403 Forbidden` error if the user is not authenticated and authorized. This correctly prevents a free-tier user from fetching the real data via JavaScript after the page has loaded.

The implementation follows the critical security principle of never sending secrets to the client.

**SEVERITY:** LOW (No issue found)

**SPECIFIC FIX**
No fix is required. This part of the code is well-architected.

---

### Q4 — CORRELATION TIMELINE LOGIC

Is the correlation timeline cross-referencing correct?

**DETAILED ANALYSIS**
The logic correctly performs temporal windowing, but the "score" is a heuristic, and the overall framing carries legal risk.

1.  **Temporal Correlation:** The core logic in `build_correlations` (`panopticon_service.py:850-929`) is sound. It correctly parses dates and uses `abs((w_date - disc_date).total_seconds())` (lines 876, 890) to check if different events fall within the `±72h` window. This is a legitimate temporal correlation.
2.  **Correlation Score:** The `correlation_score` calculation (`panopticon_service.py:905-908`) is not a statistical measure. It's an arbitrary heuristic that combines the number of related events and their average time offset. While it may be useful for ranking, calling it a "correlation score" implies a level of statistical rigor that is not present. This could be misleading to users.
3.  **False Positives:** The system is highly susceptible to producing false correlations. Any two unrelated events that happen within the 72-hour window will be linked. The requirement for at least 2 co-occurring signals (`panopticon_service.py:901`) helps, but does not eliminate this. The phrase "correlation does not imply causation" is paramount here.
4.  **Legal Risk:** This is the most significant issue. While disclaimers are present in the service (`panopticon_service.py:923`) and on the front-end (`panopticon.html:1084-1086`), the feature's name ("PANOPTICON"), tagline ("They watch us. Now we watch them."), and UI copy ("FLAGGED", "PATTERN DETECTED") create a strong implication of wrongdoing. A public figure who is "flagged" by this system could argue that the presentation is defamatory, even with fine-print disclaimers.

**SEVERITY:** MEDIUM

**SPECIFIC FIX**
1.  Rename the `correlation_score` to something more descriptive and less authoritative, such as `proximity_score` or `signal_cluster_score`.
2.  Make the legal disclaimers more prominent in the UI. A small block of text can be easily missed. Consider a modal pop-up on first use or a more visible banner.
3.  **Strongly recommend a legal review** of the feature's branding and UI terminology to assess the risk of defamation claims. Softer language like "Events of Interest" instead of "FLAGGED" might be advisable.

---

### Q5 — SCALABILITY

Will this scale under 1000 concurrent users?

**DETAILED ANALYSIS**
No, the current architecture will not scale to 1000 concurrent users and will likely fail under heavy load.

1.  **In-Memory Cache:** As detailed in Q2, the `_cache` and `_cache_lock` in `panopticon_service.py` are per-process. With multiple workers, the cache hit rate will be drastically reduced, leading to a flood of redundant external API calls. The `thundering-herd protection` is also only per-process, meaning 8 workers could still launch 8 simultaneous requests to an external API when a cache key expires.
2.  **Synchronous API Calls:** `get_dashboard_data` (`panopticon_service.py:975-984`) makes numerous network-bound calls sequentially: `get_btc_price`, `fetch_disclosures`, `fetch_whale_alerts`, etc. Each call blocks, and the total response time is the sum of all of them. For a single user, this might be a few seconds. For 1000 concurrent users, this will tie up all available worker processes, leading to extreme latency and request timeouts.
3.  **Database Query Performance:** The query in `fetch_geopolitical` (`panopticon_service.py:574-577`) uses multiple `tags.ilike("%keyword%")` clauses. Wildcard searches at the beginning of a string (`%sanction%`) are notoriously inefficient and cannot use a standard B-tree index, forcing a full table scan. On a large `Article` table, this query will be very slow and contribute to the request bottleneck.
4.  **Scheduler Background Tasks:** The scheduler (`scheduler.py`) is set to refresh data periodically (e.g., whales every 5 minutes, congress every 30). This is a good design. However, these tasks simply clear the in-memory cache (`_cache.pop(...)`) and re-run the fetch function. This doesn't pre-warm the cache; it just sets it up to be re-filled on the *next user request*. This means the first user to hit an endpoint after a cache clear will experience very high latency.

**SEVERITY:** CRITICAL

**SPECIFIC FIX**
1.  **Cache:** Immediately replace the in-memory cache with **Redis**. This is the single most important change for scalability.
2.  **API Calls:** Refactor `get_dashboard_data` to execute the independent data fetches in parallel using Python's `concurrent.futures.ThreadPoolExecutor`. This will significantly reduce the function's total execution time.
3.  **Database:** Replace the `ilike` queries with a proper full-text search (FTS) engine. For SQLite, this would be FTS5. For a more robust production setup, Elasticsearch or PostgreSQL's FTS would be better. Ensure standard indexes exist on `Article.published` and `Article.created_at`.
4.  **Scheduler:** Modify the scheduled tasks to not just clear the cache, but to fetch the new data and write it directly into the new Redis cache. This pre-warms the cache so that user requests are always fast.

```python
# scheduler.py - CONCEPTUAL FIX
# Change tasks to pre-warm the Redis cache instead of just popping keys.

def panopticon_whale_scan_task():
    from services.panopticon_service import fetch_whale_alerts
    # Assume _set_cache is now a function that writes to Redis
    from services.panopticon_service import _set_cache
    alerts = fetch_whale_alerts() # This function internally uses a fresh fetch
    _set_cache("panopticon_whales", alerts) # Now the cache is warm for users
```

---

## FINAL VERDICT

*   **How many CRITICAL issues found?**
    *   **2**: The lack of a shared, distributed cache/rate-limiter and the synchronous, slow data-fetching pipeline make the system unscalable.

*   **Top 3 changes needed before production:**
    1.  **Replace All In-Memory Stores with Redis:** Both the cache in `panopticon_service.py` and the rate limiter in `panopticon.py` must be migrated to a shared Redis instance to function correctly in a multi-process environment. This is non-negotiable for production.
    2.  **Parallelize Data Fetching:** The `get_dashboard_data` function must be refactored to fetch data from its various sources concurrently, not sequentially.
    3.  **Fix Misleading Placeholder Data:** The future-dated placeholder filings must be corrected to use historical data to maintain platform credibility.

*   **Is the legal framing adequate for a public-facing product?**
    *   **No.** While disclaimers exist, they are not sufficient to mitigate the risk posed by the aggressive branding ("PANOPTICON"), UI language ("FLAGGED"), and presentation that strongly implies wrongdoing. The potential for defamation claims is high. **A thorough legal review of the feature's name, copy, and presentation is strongly advised before launch.**