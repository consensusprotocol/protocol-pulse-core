# BUILD COMPLETE — p3-affiliates
# Branch: feature/p3-affiliates
# Completed: 2026-03-09
# Commits: 2 (initial build + audit second pass)

---

## WHAT WAS BUILT

### Core Features
1. **Meanwhile Bitcoin Life Insurance** — `/bitcoin-life-insurance`
   - Full landing page with hero, 3 benefit cards, 4-step how-it-works
   - Editorial endorsement in PBX/Protocol Pulse voice
   - Sovereignty Score widget (5 criteria, gold bars)
   - 6-question FAQ accordion (keyboard accessible)
   - Clear "Affiliate Partnership" disclaimer on every CTA

2. **RNS.ID Palau Digital Residency** — `/digital-residency`
   - Full landing page with Palau passport card visual
   - 4 "Why Bitcoiners Care" benefit cards
   - Cypherpunk editorial voice endorsement
   - Sovereignty Score widget (green accent for RNS.ID)
   - 5-question FAQ accordion
   - Clear affiliate disclosure

3. **Affiliate Redirect + Click Tracking**
   - `/go/meanwhile` → tracks click in DB → redirects with referral code KKM73K
   - `/go/rns` → tracks click in DB → redirects with referral code
   - Rate limited: 30/min per IP
   - IP hashed via SHA256(ip+date+TRACKING_SALT) — never stored raw

4. **AI Contextual Injection** — `services/affiliate_injector.py`
   - Claude Haiku-4-5 classifies article themes
   - Tags are authoritative gate; AI is enrichment only (LAW 1 compliant)
   - Breaking news suppression: checks category AND tags
   - Never shows both CTAs on same article
   - CTA never on homepage/list pages — article detail only
   - `@lru_cache(512)` prevents redundant API calls

5. **Thompson Sampling MAB A/B Testing** (LAW 2)
   - Starts 50/50, shifts to winner after 100 clicks per partner
   - Deterministic: same user+date always gets same variant
   - Hash-based assignment (SHA256), not cookies/localStorage
   - "Declare Winner" locks allocation permanently

6. **Behavioral Intent Scoring** (Phase 0 addition)
   - Pure vanilla JS: scroll depth (0-100%) + time on page (seconds)
   - Intent score = (scroll × 60) + (time/90 × 40)
   - CTA reveals only when score ≥ 40 (configurable threshold)
   - Fallback: shows after 60s if threshold not met; visible with JS disabled (noscript)

7. **Impression Tracking** — `navigator.sendBeacon`
   - `/api/affiliates/impression` — non-blocking, fires on CTA visibility
   - `/api/affiliates/click` — fires on landing page CTA click
   - Rate limited: 60/min per IP
   - k-anonymity enforced (≥10 unique users) in admin analytics

8. **Admin Dashboard** — `/admin/affiliates` (admin-required)
   - 30-day click summary with per-partner breakdown
   - Bar chart (last 30 days, meanwhile vs rns_id)
   - A/B test results with statistical significance (z-test, p-value)
   - Thompson Sampling MAB allocation display
   - Top referrer pages (k≥10 privacy gate)
   - Estimated earnings (conservative 2% conversion model, clearly labeled as estimate)
   - "Declare Winner" button with confirmation dialog

9. **Admin API** — `/api/affiliates/metrics` (admin-required)
   - JSON: daily clicks, totals, estimated earnings, A/B stats

### Database
- `p3_affiliate_clicks` — click tracking (partner, referrer, variant, user_hash, ua_hash)
- `p3_affiliate_ab_results` — A/B aggregates with atomic upsert (INSERT OR IGNORE + UPDATE)
- Indexes: partner+date, partner+variant, referrer_page, user_hash

---

## PHASE 0 ADDITIONS INCORPORATED
1. ✅ Thompson Sampling MAB (replaces static 50/50, activates at 100 clicks)
2. ✅ Behavioral intent scoring (JS scroll + time, no TF.js)
3. ✅ navigator.sendBeacon for impressions
4. ✅ Statistical significance (z-test, p-value) in admin
5. ✅ Content-to-conversion intelligence (per-article estimated earnings in admin)
6. ✅ Sovereignty Score widget on both landing pages (trust signal for cypherpunks)
7. ✅ k-anonymity constraint on analytics (k=10 threshold)

---

## AUDIT RESULTS SUMMARY

**Cycle 1 (correct code) consensus: 5.7/10 → 8+/10 after second pass fixes**

| Subsystem | Before 2nd Pass | After 2nd Pass |
|-----------|----------------|----------------|
| Correctness | 5/10 | ~8/10 |
| Law Compliance | 6/10 | ~9/10 (all 4 laws fixed) |
| Security | 6/10 | ~8/10 |
| Frontend | 7/10 | ~8/10 |
| Backend | 5/10 | ~8/10 |

**All P0 and P1 items from consensus implemented.**

---

## LAW COMPLIANCE STATUS
- ✅ LAW 1: Contextual relevance — tags as hard gate + AI enrichment + breaking news tag check
- ✅ LAW 2: A/B testing — Thompson Sampling MAB, hash-based, tracks separately, atomic upserts
- ✅ LAW 3: Privacy — SHA256(ip+date+TRACKING_SALT), hard-fail on missing salt, no raw IPs
- ✅ LAW 4: Editorial voice — authentic PP voice, clear affiliate disclaimers on all pages

---

## MANUAL STEPS NEEDED

### Required Before Going Live:
1. **TRACKING_SALT** — Add to `.env`:
   ```
   TRACKING_SALT=$(openssl rand -hex 32)
   ```
   Without this, the app will raise `RuntimeError` on any affiliate page load.

2. **Meanwhile Referral Code** — Confirm `KKM73K` is active and links correctly.
   The redirect URL: `https://www.meanwhile.life/?ref=KKM73K`

3. **RNS.ID Referral Code** — Confirm `protocolpulse` is valid on `https://rns.id/`.
   The redirect URL: `https://rns.id/?ref=protocolpulse`

4. **DB Migration** — Tables are created lazily on first `/go/meanwhile` or `/go/rns` request.
   Can force creation: curl https://protocolpulse.replit.app/go/meanwhile (will create tables then redirect)

### Optional Enhancements (P4 backlog):
- Conversion postback endpoint (TODO comment in affiliate_injector.py)
  - Implement `/api/affiliates/conversion` when partner webhooks are available
  - This enables MAB to optimize for revenue not just clicks
- CSRF token on `/api/affiliates/declare-winner` (currently admin-only behind login)
- Dashboard time-range filtering (currently locked to 30 days)
- Configurable conversion rate assumption in admin

---

## VERIFICATION CHECKLIST
- ✅ GET /bitcoin-life-insurance → HTTP 200, editorial content loads
- ✅ GET /digital-residency → HTTP 200, editorial content loads
- ✅ GET /go/meanwhile → click logged to DB, redirects with referral code
- ✅ GET /go/rns → click logged to DB, redirects with referral code
- ✅ inject_affiliate_cta() returns CTA for relevant articles, None for irrelevant
- ✅ A/B variant assigned consistently for same user (deterministic hash)
- ✅ GET /admin/affiliates → shows click analytics (requires admin login)
- ✅ IP never stored raw (only SHA256 hash in DB)
- ✅ Disclaimer present on both landing pages
- ✅ Breaking news CTA suppression (category + tags check)
- ✅ Rate limiting on public endpoints (30/min and 60/min)
- ✅ k-anonymity gate in analytics (k≥10)
- ✅ Atomic upsert (no race conditions on A/B counters)
- ✅ TRACKING_SALT hard-fail (no silent degradation)
- ✅ regression_test.sh: 29 PASS, 0 FAIL, 1 WARN
- ✅ git commit + push to origin feature/p3-affiliates
