# CONSENSUS REPORT — P3-AFFILIATES — CYCLE 1
Generated: 2026-03-09 14:20
Models: grok, gemini, gpt4o

---

## SCORES

Scores extracted by mapping each model's qualitative findings to a 1–10 scale. Models did not emit numeric scores natively, so these are synthesized from their section-level verdicts.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 5/10 | 4/10 | 5/10 | **5/10** |
| Law Compliance | 7/10 | 5/10 | 7/10 | **6/10** |
| Security | 7/10 | 5/10 | 5/10 | **6/10** |
| Frontend Quality | 8/10 | 6/10 | 7/10 | **7/10** |
| Backend Quality | 5/10 | 5/10 | 5/10 | **5/10** |
| **Overall** | **6.4/10** | **5.0/10** | **5.8/10** | **5.7/10** |

---

## UNANIMOUS FINDINGS
*All 3 models flagged these. Implement unconditionally.*

---

### U1 — Race Condition in A/B Counter Increments (Data Loss Under Load)
**File:** `services/affiliate_injector.py` — `_increment_ab_impressions()` and `_increment_ab_clicks()` (~lines 410–473)
**What it is:** Both functions use a non-atomic SELECT-then-INSERT/UPDATE pattern. Under concurrent load, two workers can both observe no existing row, both attempt INSERT, causing a `UniqueConstraint` violation. The `rollback()` silently drops the losing write. A/B test data is corrupted and undercounts are guaranteed at scale.
**What to change:** Replace with a single atomic upsert. For PostgreSQL use `INSERT ... ON CONFLICT DO UPDATE SET count = count + 1`. For SQLite use `INSERT OR REPLACE` with a recalculated total, or use `UPDATE ... WHERE` + insert-if-zero-rows pattern with a row-level lock. No try/catch band-aid — the fix must be structural.

---

### U2 — Hardcoded Default Tracking Salt Fatally Weakens Privacy
**File:** `services/affiliate_injector.py` ~line 335
**What it is:** `TRACKING_SALT` falls back to the hardcoded literal `"pp-affiliate-default-salt-2026"` when the env var is absent. Any deployment missing that env var shares an identical salt with every other deployment, making all hashed IPs predictable and reversible via rainbow table. This violates LAW 3's intent entirely.
**What to change:** Remove the default. Replace with:
```python
TRACKING_SALT = os.environ["TRACKING_SALT"]  # hard fail on missing
```
Add a startup assertion. Add it to `.env.example` with a note to generate via `openssl rand -hex 32`. If defensive coding is preferred: raise `RuntimeError("TRACKING_SALT must be set")` rather than silently degrading.

---

### U3 — Admin Route Authentication Cannot Be Verified / Must Be Confirmed
**File:** Route controller for `/admin/affiliates` (not present in audit package)
**What it is:** All three models flagged that the admin analytics route implementation was not provided. The route exposes all affiliate analytics, A/B results, winner-declaration, and k-anon referrer data. If not protected by the existing admin middleware, this is a critical authentication bypass.
**What to change:** Confirm the route is decorated with the project's admin auth guard. The decorator must be visible in the route definition — not just assumed from middleware ordering. Add an explicit integration test that requests `/admin/affiliates` without auth credentials and asserts a `401`/`403`/redirect response.

---

### U4 — Landing Page JS Sends Click Events to Impression Endpoint (Broken Metrics)
**File:** `core/templates/bitcoin_life_insurance.html` ~line 609, `core/templates/digital_residency.html` ~line 631
**What it is:** The `trackAffClick()` function (misnamed) fires a beacon to `/api/affiliates/impression` when a user clicks the final partner link. This semantically poisons the impression counter with click events. Every actual conversion candidate inflates impression counts, making CTR calculations wrong in both directions.
**What to change:** Either (a) rename the endpoint call to `/api/affiliates/click` and wire a proper click handler, or (b) remove the JS beacon entirely if the server-side `/go/` redirect already logs the click (which it should). Do not log the same event twice.

---

### U5 — `converted` Column Is Never Written (Dead Schema)
**File:** `core/models.py` ~line 496, `services/affiliate_injector.py` (no write found)
**What it is:** The `P3AffiliateClick` model defines a `converted` boolean column that tracks whether the user completed the partner action. It defaults to `0` and is never updated anywhere in the codebase. The column and the concept are spec-required but entirely unimplemented.
**What to change:** Either (a) implement conversion postback: add a `/api/affiliates/conversion` endpoint that partners can call (or implement a webhook receiver), validates a shared secret, and flips `converted = 1` for the matching `user_hash` + partner + date, OR (b) if partner webhooks are not yet available, add a clear `TODO(p4):` comment and remove the column from any analytics display that implies conversion data exists, so the dashboard doesn't silently show 0% conversions as if it's real data.

---

### U6 — No Rate Limiting on Public Impression/Click Endpoints
**File:** `/api/affiliates/impression` endpoint (and `/go/` redirect when located)
**What it is:** All three models noted the absence of rate limiting on publicly accessible endpoints that perform database writes. A malicious actor can flood `p3_affiliate_ab_results` with fake impressions at zero cost, permanently corrupting A/B test signal and potentially degrading database performance.
**What to change:** Apply Flask-Limiter (or equivalent) to `/api/affiliates/impression` and `/go/<partner>`. A reasonable limit is `60/minute per IP` for impression beacons. For the redirect endpoint, `30/minute per IP` is sufficient. Log rate-limit hits at WARN level.

---

## MAJORITY FINDINGS
*2 of 3 models flagged these. Implement unless there is a compelling reason not to.*

---

### M1 — Hardcoded 2% Conversion Rate in Earnings Estimates (Gemini + Grok)
**File:** `core/templates/admin_affiliates.html` ~lines 377–379
**What it is:** Estimated earnings displayed to the admin are calculated using a static 2% conversion rate. This is fictional and potentially misleading for business decisions.
**Recommendation:** Make this a configurable value stored in a settings table or `.env`, defaulting to 2% but editable from the admin panel. Long-term, derive it from actual `converted = 1` rows when conversion tracking is implemented (U5 above).

---

### M2 — MAB Activation Uses Wrong Signal: Impressions Instead of Clicks (Gemini + GPT-4o)
**File:** `services/affiliate_injector.py` ~line 172
**What it is:** Thompson Sampling weights activate after 100 *impressions*. The addendum/spec says 100 *clicks*. Clicks are a far stronger signal of user intent. Activating MAB on impressions means the bandit starts exploiting before it has meaningful conversion signal, potentially locking in a variant based on noise.
**Recommendation:** Change the threshold check to compare against total click count (`sum of ab_clicks`) for that partner, not impression count. Add a comment citing the spec reference.

---

### M3 — Breaking News Suppression Too Narrow (GPT-4o + Grok)
**File:** `services/affiliate_injector.py` ~lines 305–308
**What it is:** Breaking news is only excluded by checking `article_category`. If a breaking story is categorized as "Markets" or "Regulation" but tagged `breaking-news`, the CTA still fires. This is a LAW 1 correctness issue with real editorial risk.
**Recommendation:** Extend the check to also inspect `article.tags` for `"breaking"`, `"breaking-news"`, `"urgent"`. Consider also checking a `is_breaking` boolean field if one exists on the Article model.

---

### M4 — Brittle Click URL Mutation in Article Template (Gemini + GPT-4o)
**File:** `core/templates/article_detail.html` ~lines 649–656
**What it is:** The click handler appends `?ref=...&v=...` or `&ref=...&v=...` to the href, but does not account for: (a) existing query parameters containing `ref` or `v`, causing duplicates; (b) middle-click / right-click "open in new tab", which bypasses the click listener entirely and fires the link without tracking params.
**Recommendation:** Use the `URL` Web API to construct the final href cleanly:
```javascript
const url = new URL(link.href, window.location.origin);
url.searchParams.set('ref', refSlug);
url.searchParams.set('v', variant);
link.href = url.toString();
```
This handles existing params safely. For middle-click, set `link.href` at CTA render time (not on click), so the URL is correct regardless of how the link is opened.

---

### M5 — Missing Route Implementations for Core Flows (GPT-4o + Grok)
**File:** Route handlers for `/go/<partner>`, `/admin/affiliates`, `/api/affiliates/metrics`, `/api/affiliates/declare-winner`
**What it is:** Multiple backend routes referenced in templates and the spec have no route code in the audit package. This makes it impossible to verify the core click-tracking flow, admin auth, or metrics data shape end-to-end.
**Recommendation:** Either provide these files for audit, or assert in the second pass that they exist, are tested, and are covered by the integration test suite. Do not merge without them.

---

## UNIQUE INSIGHTS
*Only 1 model caught these. Evaluated individually.*

---

### I1 — Variant B Hardcoded on Landing Pages (Gemini only)
**File:** `core/templates/bitcoin_life_insurance.html` ~line 609, `digital_residency.html` ~line 630
**What it is:** Gemini caught that `trackAffClick()` hardcodes `variant: 'B'` in its payload, regardless of which variant the user actually saw. This means all final click-throughs from landing pages are misattributed to variant B in the A/B results.
**Assessment: IMPLEMENT — critical.** This is arguably the most damaging correctness bug in the entire feature. The A/B test can never produce a valid winner because variant A users are logged as variant B on conversion. This deserves P0 status. The fix: pass the variant through the URL (e.g., `/go/meanwhile?v=A` or stored in `sessionStorage` set during the initial CTA render) and read it on the landing page.

---

### I2 — `@lru_cache` on Article Classifier is an Excellent Optimization (Gemini only)
**File:** `services/affiliate_injector.py` — `_classify_article()`
**What it is:** Gemini noted this as a strength. The LRU cache prevents redundant Claude API calls for the same article, reducing cost and latency.
**Assessment: VALIDATE — do not touch.** This is correct and intentional. Ensure the cache key includes `article_id` and the cache is appropriately sized. No action needed, listed in Validated Strengths.

---

### I3 — JS-Disabled Fallback: CTA Permanently Invisible (GPT-4o only)
**File:** `core/templates/article_detail.html` ~line 227
**What it is:** CTA container is `opacity:0` inline style with no `<noscript>` override. Users with JS disabled never see any CTA.
**Assessment: IMPLEMENT (P2).** The addendum specifies a JS-disabled fallback. Fix: add `<noscript><style>.affiliate-cta-block { opacity: 1 !important; }</style></noscript>` or restructure so the container is visible by default and JS hides-then-reveals it.

---

### I4 — N+1 Write Pattern in Click Tracking Under High Load (Grok only)
**File:** `services/affiliate_injector.py` ~line 372
**What it is:** Each click performs a synchronous DB write in the request path. At 1000 concurrent users this could bottleneck.
**Assessment: INVESTIGATE FURTHER.** At current scale this is likely fine — a single INSERT per click is standard. However, if the spec genuinely targets high concurrency, moving to an async write queue (Celery task, Redis buffer) is the right long-term architecture. For now: P2 — add a TODO comment and instrument with a timer log.

---

### I5 — AI Classification Can Trigger CTA Without Tag Match (GPT-4o only)
**File:** `services/affiliate_injector.py` ~lines 317–324
**What it is:** Tag filtering is only a fallback if AI says no. AI saying yes is sufficient to show the CTA even if required tags are absent. This inverts the intended logic — tags should be a hard gate, AI a soft enrichment.
**Assessment: IMPLEMENT (P1).** This is a LAW 1 correctness issue. The spec implies tags are the authoritative gate. Refactor so: (a) required tags must be present OR (b) AI classification is required AND at least one related tag is present. "AI-only, no tags" should not qualify.

---

### I6 — `declareWinner` JS Uses Global `event` Unreliably (GPT-4o only)
**File:** `core/templates/admin_affiliates.html` ~line 635
**What it is:** `declareWinner()` references the global `event` object from an inline `onclick`. This is browser-dependent and can silently fail in strict-mode or certain browser versions, leaving `btn` null and breaking UI feedback while still firing the fetch.
**Assessment: IMPLEMENT (P2).** Pass `event` explicitly: `onclick="declareWinner(event)"` and receive it as a parameter. One-line fix.

---

### I7 — Missing Index on `referrer_page`, `user_hash` Columns (GPT-4o only)
**File:** `core/models.py` ~lines 501–504
**What it is:** Analytics queries will filter and aggregate by `referrer_page` (top referrers) and `user_hash` (distinct user counts for k-anon). Neither has an index. The stack rule explicitly requires indexes on all sort/filter columns.
**Assessment: IMPLEMENT (P1).** Add: `Index('ix_p3_affiliate_clicks_referrer', 'referrer_page')` and `Index('ix_p3_affiliate_clicks_user_hash', 'user_hash')`. Include in the Alembic migration.

---

## CONFLICTS
*Models gave contradictory assessments. Tiebreaker applied.*

---

### C1 — Partner Prioritization Logic (Meanwhile always wins over RNS)
- **Grok:** Flags this as a LAW 1 violation — "randomness or balance implied in LAW 1."
- **Gemini + GPT-4o:** Do not flag this as a violation.
- **Tiebreaker: Grok is wrong here.** LAW 1 says contextual relevance only — it does not mandate fairness between partners. A deterministic tie-break when both partners qualify is architecturally valid and preferable to random selection (which introduces variance). The real fix for partner balance is to let MAB weights handle relative exposure over time, which the code already implements. No action needed on tie-break logic itself.

---

### C2 — Per-Day vs. Per-Session Hash for A/B Assignment
- **GPT-4o:** Flags `user_hash` being IP+date+salt as "per-day, not per-session" and questions compliance with the law.
- **Grok + Gemini:** Accept this as compliant — the spec explicitly says "hash of IP+date."
- **Tiebreaker: Grok and Gemini are correct.** The GOSPEL spec explicitly defines the hash as `IP+date+salt`. GPT-4o is applying a stricter interpretation than the spec requires. "Per-day" and "per-session" are functionally equivalent for anonymous users where session state isn't persisted server-side. No action needed.

---

### C3 — Table Naming Convention (p3_ prefix vs. spec names)
- **GPT-4o:** Flags that table names use `p3_affiliate_clicks` instead of spec's `affiliate_clicks` as spec drift.
- **Grok + Gemini:** Do not flag this.
- **Tiebreaker: GPT-4o is technically correct but the concern is low-priority.** The `p3_` prefix is a reasonable namespace convention for a Phase 3 feature and avoids table name collision. However, if the GOSPEL explicitly specifies `affiliate_clicks`, the code should match it or the GOSPEL should be updated. **Recommendation: Update GOSPEL.md to reflect `p3_affiliate_clicks` as the canonical name** rather than renaming the table. Document this as an intentional namespace prefix. P3 item.

---

## VALIDATED STRENGTHS
*All models confirmed these are excellent. Do NOT change them in the second pass.*

1. **Claude Haiku integration with timeout, retry, and graceful keyword fallback** — `services/affiliate_injector.py:81–143`. Robust external API handling. Leave as-is.
2. **`@lru_cache` on `_classify_article()`** — Excellent optimization reducing API costs. Leave as-is.
3. **SHA256 IP hashing with env-sourced salt** — The *pattern* is correct (just fix the missing-env fallback per U2). The hashing logic itself is sound.
4. **Editorial voice and disclaimer implementation on landing pages** — `bitcoin_life_insurance.html` and `digital_residency.html` match spec. Do not alter tone or structure.
5. **Thompson Sampling MAB framework** — Architecturally correct and advanced. The threshold bug (M2) is a one-line fix; the MAB structure itself is strong.
6. **k-anonymity enforcement for referrer data in admin dashboard** — Privacy-first design. Leave enforcement logic untouched.
7. **Logging with context** — Error logging includes `article_id`, partner, error message. Sufficient for production debugging. Do not reduce verbosity.
8. **Dark, polished UI design** — Admin dashboard and landing pages are visually excellent. No layout or design changes needed.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Determination |
|---|---|---|
| **LAW 1: Contextual Relevance Only** | ⚠️ PARTIAL VIOLATION | Breaking news check too narrow (tags not checked). AI-only classification can bypass tag gate. Both are correctness failures with editorial risk. |
| **LAW 2: A/B Test Every CTA Variant** | ❌ VIOLATION | Two compounding bugs: (1) landing page hardcodes `variant: 'B'` making test unresolvable; (2) MAB activates on impressions not clicks. The A/B test framework exists but produces invalid data. |
| **LAW 3: Click Tracking Hashes IPs — Never Store Raw** | ⚠️ PARTIAL | Pattern is correct. Critically undermined by hardcoded fallback salt (U2). With that fixed: COMPLIANT. |
| **LAW 4: Editorial Voice — Never Feel Like Ads** | ✅ COMPLIANT | Landing pages, CTAs, and disclaimers all pass. Unanimous across all three models. |

---

## SECURITY CONSENSUS

Priority-ordered issues that 2+ models flagged:

| Priority | Issue | Models |
|---|---|---|
| **P0** | Hardcoded default salt breaks IP hash privacy guarantee | All 3 |
| **P0** | Admin route authentication unverifiable — potential open analytics exposure | All 3 |
| **P1** | No rate limiting on public impression/click endpoints — DB flood and A/B pollution vector | All 3 |
| **P2** | `referrer_page` stored unvalidated from client input | Gemini + GPT-4o |
| **P2** | `declareWinner` POST lacks CSRF protection | Grok (unique, but valid) |

---

## WORLD-CLASS GAP CONSENSUS
*Only items 2+ models raised.*

1. **No true conversion tracking — the system optimizes for clicks, not revenue.** (Gemini + Grok) The `converted` column exists but is never written. Without server-to-server conversion postbacks from partners, the business cannot measure what actually generates revenue. A click-optimized MAB will diverge from a revenue-optimized MAB. This is the single largest gap between the current implementation and a world-class affiliate product.

2. **Admin dashboard lacks configurability and drill-down.** (Gemini + Grok) A professional marketing team needs: configurable conversion rate assumption, ability to override MAB weights manually, per-article CTA performance breakdown, and time-range filtering on all charts. Currently the dashboard is read-only with hardcoded assumptions.

3. **A/B test data integrity is insufficient for a valid winner declaration.** (Gemini + GPT-4o) Between the hardcoded variant B, the race condition data loss, and the impression/click endpoint confusion, the `declareWinner` button in the admin panel cannot be trusted to reflect reality. Winner declaration should be gated behind a minimum statistical confidence threshold (e.g., p < 0.05 via a chi-squared test), not just raw counts.

---

## FINAL ACTION PLAN

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Replace SELECT-then-INSERT/UPDATE in A/B counters with atomic upsert | `services/affiliate_injector.py:410–473` | All 3 | Guarantees data loss under any concurrent load; corrupts A/B test permanently |
| **P0 CRITICAL** | Remove hardcoded default salt; hard-fail on missing env var | `services/affiliate_injector.py:335` | All 3 | Shared salt = predictable hashes = LAW 3 violated across all deployments |
| **P0 CRITICAL** | Fix landing page `variant: 'B'` hardcode; pass real variant through URL param or sessionStorage | `bitcoin_life_insurance.html:609`, `digital_residency.html:630` | Gemini (unique but critical) | A/B test can never resolve; all conversions misattributed; LAW 2 violated |
| **P0 CRITICAL** | Confirm admin route has auth guard; add integration test asserting 401/403 without credentials | Route controller (missing) | All 3 | Potential open exposure of all affiliate analytics and winner-declaration endpoint |
| **P1 HIGH** | Add rate limiting (60/min per IP) to `/api/affiliates/impression` and `/go/<partner>` | Endpoint decorators | All 3 | DB flood and A/B data pollution attack with zero cost to attacker |
| **P1 HIGH** | Fix `trackAffClick()` to call click endpoint, not impression endpoint | `bitcoin_life_insurance.html:609`, `digital_residency.html:631` | All 3 | Impression metrics permanently inflated; click-through rates uncalculable |
| **P1 HIGH** | Change MAB activation threshold from impression count to click count | `services/affiliate_injector.py:172` | Gemini + GPT-4o | MAB exploits on noise signal; spec explicitly says clicks |
| **P1 HIGH** | Extend breaking news suppression to check `article.tags` for `"breaking"`, `"breaking-news"`, `"urgent"` | `services/affiliate_injector.py:305–308` | GPT-4o + Grok | CTAs fire on breaking stories tagged correctly but miscategorized; LAW 1 |
| **P1 HIGH** | Fix brittle URL mutation in click handler; use `URL` Web API; set href at render time not click time | `article_detail.html:649–656` | Gemini + GPT-4o | Middle-click/right-click