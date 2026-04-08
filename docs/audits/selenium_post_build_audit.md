# Selenium Intelligence Scraper — Post-Build Audit

## Date: 2026-04-08
## Auditors: Gemini 2.5 Flash, Claude Opus 4.6 (synthesis)
## Note: Grok 3 Mini API returned 401 (expired key), GPT-4o returned 429 (quota exceeded). Audit proceeds with 2-model consensus.
## Status: FIXES APPLIED — see bottom of document

## Files Audited
- `services/selenium_intelligence_scraper.py` (1062 lines)
- `core/routes_api.py` lines 7064-7134 (intelligence chart endpoints)
- `core/routes_api.py` lines 5546-5702 (`_fetch_onchain()` with pro_metrics_cache integration)
- `templates/signal_terminal.html` lines 1356-1372 (on-chain charts panel) + lines 3015-3046 (chart JS)

---

## AXIS SCORES SUMMARY

| Axis | Gemini | Claude | Consensus |
|------|--------|--------|-----------|
| 1. Detection Risk | WARN | WARN | **WARN** |
| 2. Error Handling | WARN | WARN | **WARN** |
| 3. Data Accuracy | WARN | WARN | **WARN** |
| 4. Memory Leaks | WARN | PASS | **PASS** |
| 5. Rate Limiting | PASS | PASS | **PASS** |
| 6. Security | FAIL | FAIL | **FAIL** |
| 7. Frontend Integration | FAIL | FAIL | **FAIL** |
| 8. Cron Reliability | WARN | WARN | **WARN** |

**Overall: 2 FAIL, 4 WARN, 2 PASS**

---

## CONSENSUS FINDINGS (Both Models Agree)

### FAIL-1: Unauthenticated Chart API Endpoints
**Severity: CRITICAL**
**Files:** `core/routes_api.py:7081-7133`

Both auditors independently identified that `/api/intelligence/charts` and `/api/intelligence/charts/<filename>` have **zero authentication checks**. Any anonymous user can:
1. Hit `/api/intelligence/charts` to list all available chart screenshots
2. Hit `/api/intelligence/charts/{filename}` to download the full-resolution, unblurred PNG

This completely bypasses the Commander paywall ($29/mo). The Jinja2 `filter:blur(6px)` in `signal_terminal.html:3034` is purely cosmetic — the actual image data is served unprotected.

**Impact:** Revenue loss. Free users can access premium Commander-gated on-chain charts.

**Fix Required:** Add Commander auth check to both endpoints. Return 403 for non-Commander users, or serve a server-side blurred version.

---

### FAIL-2: Screenshots May Contain Sensitive Data
**Severity: HIGH**
**Files:** `services/selenium_intelligence_scraper.py:337-343, 286, 473-477`

Screenshots are saved with **no redaction** of page content. Both auditors flagged:
- If the browser has any cached credentials or cookies, screenshots could capture session tokens, account info, or PII
- These screenshots are then served publicly via the unauthenticated API (compounding FAIL-1)
- The `full_page=False` flag limits scope but still captures the viewport

**Impact:** Potential credential/PII exposure via public API.

**Fix Required:** Either (a) ensure fresh browser context with no state, (b) crop screenshots to chart area only, or (c) gate the screenshot API behind auth.

---

### WARN-1: navigator.plugins Fingerprint Leak
**Severity: MEDIUM**
**Files:** `services/selenium_intelligence_scraper.py:113`

Both auditors flagged `navigator.plugins` returning `[1, 2, 3, 4, 5]` (plain integers) instead of proper `PluginArray` of `Plugin` objects. Modern bot detectors (Cloudflare, DataDome, PerimeterX) check:
- `navigator.plugins[0] instanceof Plugin` → returns `false` for integer array
- `navigator.plugins.length` type check
- Plugin object properties (name, description, filename)

This is a detectable automation fingerprint that could trigger blocking.

---

### WARN-2: Outdated User-Agent Strings
**Severity: MEDIUM**
**Files:** `services/selenium_intelligence_scraper.py:42-51`

User agents are from 2024 (Chrome 121-124, Firefox 125, Safari 17.2-17.3). As of April 2026, these are ~2 years old. Bot detectors increasingly flag outdated browser versions as suspicious. Both auditors recommend updating to current Chrome 130+/Firefox 134+ versions.

---

### WARN-3: Fixed 8s Wait Instead of Event-Driven
**Severity: MEDIUM**
**Files:** `services/selenium_intelligence_scraper.py:271, 456`

Both auditors flagged `page.wait_for_timeout(8000)` as fragile:
- If API responds faster → wasted time
- If API responds slower → data missed
- Better: use `page.wait_for_response(url_pattern, timeout=15000)` or `page.expect_response()`

---

### WARN-4: ISO Timestamp String Comparison for Staleness
**Severity: MEDIUM**
**Files:** `core/routes_api.py:5603-5607`

Both auditors flagged the staleness check:
```python
_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "+00:00"
# ...
if _mvrv_entry.get("scraped_at", "") > _cutoff:
```
This performs lexicographic string comparison. It works correctly IF both timestamps are in identical ISO format with `+00:00` suffix. However:
- `datetime.now(timezone.utc).isoformat()` (used in scraper) produces `2026-04-08T04:00:00+00:00`
- `datetime.utcnow().isoformat() + "+00:00"` (used in route) produces `2026-04-08T04:00:00+00:00`
- These formats happen to match, but it's fragile. Any format variation breaks the comparison.

**Recommendation:** Parse both to datetime objects for comparison.

---

### PASS-1: Rate Limiting (Consensus)
Both auditors rated PASS. Once-daily scraping at 4am ET with 3-10s human delays between page loads is extremely respectful. No ban risk.

### PASS-2: Browser Lifecycle Management
Gemini rated WARN (concerned about zombie processes), Claude rated PASS. Investigation:
- The `HeadlessBrowser` context manager (`__enter__`/`__exit__`) properly closes browser in `finally` block
- Individual pages are closed in `finally` blocks (`_scrape_chart` methods)
- The orchestrator uses `with HeadlessBrowser() as browser:` which guarantees cleanup
- **Edge case:** If Python is killed by SIGKILL (OOM killer), `__exit__` won't run. This is acceptable for a daily cron.

**Consensus: PASS** — the lifecycle management is sound for the use case.

---

## DISPUTED FINDINGS

### Memory Leaks
- **Gemini:** WARN — concerned about resource accumulation within shared browser instance
- **Claude:** PASS — pages are properly closed in finally blocks, context manager ensures cleanup
- **Resolution:** Manual code review confirms pages are closed in `finally` blocks at lines 290-291 and 480-481. The context manager at line 966 (`with HeadlessBrowser() as browser:`) guarantees browser cleanup. **Resolved as PASS.**

---

## CRITICAL ISSUES (Must Fix)

### 1. Add Commander Auth to Chart API Endpoints
**Priority: P0 — Revenue/security impact**
**File:** `core/routes_api.py`

Both `/api/intelligence/charts` and `/api/intelligence/charts/<filename>` must require Commander authentication. Non-Commander users should receive 403 or a blurred placeholder.

### 2. Gate or Redact Screenshots
**Priority: P1 — Security**
**File:** `services/selenium_intelligence_scraper.py`

Either:
- (a) Crop screenshots to chart canvas element only (reduces exposure)
- (b) Add auth to the serving endpoint (addressed by fix #1)
- (c) Both (recommended)

---

## WARNINGS (Should Fix)

### 3. Fix navigator.plugins Override
**Priority: P2 — Stealth**
**File:** `services/selenium_intelligence_scraper.py:110-114`

Replace `[1, 2, 3, 4, 5]` with proper PluginArray mock, or better: use `playwright-stealth` package which handles all fingerprint overrides.

### 4. Update User-Agent Strings to 2026 Versions
**Priority: P2 — Stealth**
**File:** `services/selenium_intelligence_scraper.py:42-51`

Update to Chrome 132+, Firefox 135+, Safari 18+ (current as of April 2026).

### 5. Replace Fixed Timeout with Event-Driven Wait
**Priority: P3 — Reliability**
**Files:** `services/selenium_intelligence_scraper.py:271, 456`

Use `page.expect_response()` or `page.wait_for_response()` instead of `page.wait_for_timeout(8000)`.

### 6. Fix Timestamp Comparison to Use datetime Objects
**Priority: P3 — Data accuracy**
**File:** `core/routes_api.py:5603-5607`

Parse ISO strings to datetime objects before comparing.

### 7. Remove Hardcoded Absolute Path
**Priority: P4 — Maintainability**
**File:** `core/routes_api.py:5601`

Replace `/home/ultron/protocol_pulse/data/pro_metrics_cache.json` with path relative to project root.

---

## RECOMMENDATIONS (Prioritized)

1. **P0:** Add Commander auth to `/api/intelligence/charts` and `/api/intelligence/charts/<filename>`
2. **P1:** Crop screenshots to chart element only
3. **P2:** Install and use `playwright-stealth` for comprehensive fingerprint evasion
4. **P2:** Update user-agent strings to 2026 browser versions
5. **P3:** Replace `wait_for_timeout(8000)` with event-driven response wait
6. **P3:** Use proper datetime parsing for staleness check
7. **P3:** Add retry logic (3x with exponential backoff) for transient scraping failures
8. **P4:** Add monitoring/alerting for cron job failures (check if pro_metrics_cache.json updated within 25 hours)
9. **P4:** Remove hardcoded absolute path in routes_api.py

---

## APPENDIX: Auditor Raw Outputs

### Gemini 2.5 Flash
- Detection Risk: WARN (navigator.plugins flaw, small UA pool)
- Error Handling: WARN (fixed timeout, shared browser crash risk)
- Data Accuracy: WARN (tooltip fragility, string timestamp comparison)
- Memory Leaks: WARN (page/context cleanup concern)
- Rate Limiting: PASS
- Security: FAIL (screenshots + unauthenticated API)
- Frontend Integration: FAIL (paywall bypass via direct API)
- Cron Reliability: WARN (no retry, no monitoring)

### Claude Opus 4.6
- Detection Risk: WARN (navigator.plugins, outdated UAs)
- Error Handling: WARN (fixed timeout)
- Data Accuracy: WARN (string timestamp comparison)
- Memory Leaks: PASS (lifecycle management is sound)
- Rate Limiting: PASS
- Security: FAIL (screenshots + unauthenticated API)
- Frontend Integration: FAIL (paywall bypass via direct API)
- Cron Reliability: WARN (no retry logic)

---

## FIXES APPLIED (2026-04-08)

### FIX 1: Commander Auth on Chart API (P0 — FAIL-1)
**Files modified:** `core/routes_api.py` lines 7081-7086, 7128-7133
- Added `_commander_required()` check to both `/api/intelligence/charts` and `/api/intelligence/charts/<filename>`
- Non-Commander users now receive 401 JSON error instead of raw chart data
- Frontend JS updated to handle 401 gracefully (`signal_terminal.html` line 3020)

### FIX 2: Realistic navigator.plugins Mock (P2 — WARN-1)
**File modified:** `services/selenium_intelligence_scraper.py` lines 110-128
- Replaced `[1, 2, 3, 4, 5]` with proper PluginArray/Plugin prototype chain
- 5 realistic plugins: PDF Viewer, Chrome PDF Viewer, Chromium PDF Viewer, Edge PDF Viewer, WebKit PDF
- `navigator.plugins[0] instanceof Plugin` now returns `true`

### FIX 3: Updated User-Agent Strings (P2 — WARN-2)
**File modified:** `services/selenium_intelligence_scraper.py` lines 42-51
- Updated Chrome 121-124 → Chrome 132-134
- Updated Firefox 125 → Firefox 135
- Updated Safari 17.2-17.3 → Safari 18.2-18.3
- Updated macOS 14_4 → 14_7 and 15_3

### Remaining Open Items
- P1: Crop screenshots to chart element (not yet applied)
- P3: Replace `wait_for_timeout(8000)` with event-driven wait
- P3: Fix ISO timestamp string comparison to use datetime objects
- P3: Add retry logic for transient failures
- P4: Add cron monitoring/alerting
- P4: Remove hardcoded absolute path
