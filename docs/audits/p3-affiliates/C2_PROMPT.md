# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: p3-affiliates
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE REVIEW REPORT: PROTOCOL PULSE P3-AFFILIATES FEATURE

#### SECTION 1: CORRECTNESS
Walking through the main user flow for affiliate CTA injection and tracking:

1. **User Flow Step 1: Article View with CTA Injection (services/affiliate_injector.py)**
   - The `inject_affiliate_cta` function (lines 290-356) correctly identifies relevant articles for affiliate CTAs using AI classification via Claude Haiku (line 315) and falls back to tag-based checks (lines 321-322). However, there’s a logic error in prioritization: if both `meanwhile_ok` and `rns_ok` are true, `meanwhile` always wins (line 327), which violates the randomness or balance implied in LAW 1 for avoiding bias between partners.
   - **Edge Case**: If `article_tags` or `article_category` is empty or malformed, the checks still pass without errors (lines 306-308), but this could lead to incorrect exclusions (e.g., missing "breaking" category).
   - **Silent Failure**: If Claude API fails (line 134), the fallback to keyword matching is overly simplistic and may misclassify content, leading to irrelevant CTAs without logging the failure severity for debugging.

2. **User Flow Step 2: A/B Variant Assignment (services/affiliate_injector.py)**
   - The `_get_ab_variant` function (lines 216-225) uses a deterministic hash of user data with MAB weights from `_get_mab_weights` (lines 149-198). This works for consistent user experience, but there’s a **race condition** risk: multiple concurrent requests for the same user could read outdated MAB weights from the DB before updates are committed (no transaction locking in line 157-162), potentially skewing variant distribution.
   - **Edge Case**: If DB access fails (line 199-201), it silently returns 50/50 split without logging, which could mask persistent DB issues in production.

3. **User Flow Step 3: Click Tracking (services/affiliate_injector.py)**
   - The `track_click` function (lines 361-396) hashes IP with salt (line 366) and stores click data. It correctly avoids storing raw IPs, but there’s an **N+1 query issue**: it performs a separate DB write per click without batching (line 372), which could bottleneck under high traffic (~1000 concurrent users as per spec).
   - **Silent Failure**: If DB commit fails (line 385), it rolls back but doesn’t retry or notify, risking data loss for analytics.

4. **User Flow Step 4: Admin Analytics Dashboard (core/templates/admin_affiliates.html)**
   - The dashboard (lines 354-549) displays totals and A/B stats, but there’s a **logic error** in estimated earnings calculation (lines 377-379): it assumes a flat 2% conversion rate without dynamic adjustment based on historical data, which could mislead revenue projections.
   - **Edge Case**: If `top_refs` is empty due to k-anonymity (line 536), the UI shows a message, but there’s no fallback to aggregate data differently, potentially hiding useful insights.

**Summary**: The code mostly functions as claimed but has logic errors in partner prioritization, race conditions in MAB weight updates, N+1 query inefficiencies, and unhandled edge cases that could break analytics or CTA relevance in production.

#### SECTION 2: LAW COMPLIANCE
- **LAW 1: Contextual Relevance Only — No Random Banner Spam**
  - **PARTIAL COMPLIANCE**: The code uses Claude Haiku for content analysis (services/affiliate_injector.py:315) and restricts CTAs to specific tags (lines 321-322), ensuring relevance. However, the hardcoded prioritization of `meanwhile` over `rns_id` (line 327) violates the implied fairness or randomness in showing CTAs. Additionally, breaking news exclusion relies on string matching (line 308), which could fail if categories are misspelled or formatted differently.
- **LAW 2: A/B Test Every CTA Variant**
  - **COMPLIANT**: A/B testing is implemented with a 50/50 split initially, transitioning to Thompson Sampling MAB after sufficient data (services/affiliate_injector.py:149-198). Variant assignment is consistent per user session via hash (line 223), and results are tracked in `affiliate_clicks` table (line 372).
- **LAW 3: Click Tracking Hashes IPs — Never Store Raw**
  - **COMPLIANT**: IP is hashed with SHA256 and a salt from .env (services/affiliate_injector.py:336-337), ensuring raw IPs are never stored. User agent is also hashed (line 367), maintaining privacy-first design.
- **LAW 4: Editorial Voice — Never Feel Like Ads**
  - **COMPLIANT**: Landing pages (core/templates/bitcoin_life_insurance.html and digital_residency.html) use editorial tones as specified (e.g., lines 117-119 in bitcoin_life_insurance.html for Matty Ice voice). CTAs in articles are natural (services/affiliate_injector.py:238-259 for inline text). Disclaimers are present on all pages (e.g., bitcoin_life_insurance.html:128-129).

**Summary**: Mostly compliant, with a partial violation in LAW 1 due to biased partner prioritization and potential breaking news misclassification.

#### SECTION 3: SECURITY
- **SQL Injection**: No direct SQL injection ri

## GEMINI — CYCLE 1 OUTPUT
An exhaustive, forensic code review of the `p3-affiliates` feature follows.

### SECTION 1: CORRECTNESS

The code is generally well-structured, but several critical logic flaws and race conditions would cause significant issues in a production environment.

*   **Critical Race Condition:** The functions `_increment_ab_impressions` and `_increment_ab_clicks` in `services/affiliate_injector.py` (lines 410-473) use a non-atomic "SELECT, then INSERT/UPDATE" pattern. Under concurrent load, two requests could simultaneously check for a new partner/variant, both find nothing, and then both attempt to `INSERT`. This will trigger a `UniqueConstraint` violation, and due to the `rollback`, one of the impressions/clicks will be lost. This fundamentally undermines the integrity of the A/B test data. An atomic "upsert" operation is required.
*   **Flawed A/B Attribution Logic:** The JavaScript on the landing pages (`bitcoin_life_insurance.html:609`, `digital_residency.html:630`) contains a major logic error. The `trackAffClick` function is not only misnamed (it sends data to the `/api/affiliates/impression` endpoint) but it also hardcodes `variant: 'B'`. This breaks the A/B test attribution chain. Any user who clicks a CTA, visits the landing page, and then clicks the final affiliate link will have their action misattributed to Variant B, regardless of which variant they originally saw.
*   **Brittle Link Modification:** The JavaScript in `article_detail.html:650-657` modifies the affiliate link `href` attribute within a `click` event listener. This is not robust. Users who middle-click or right-click to "Open in New Tab" may not get the modified URL with the necessary tracking parameters, leading to untracked clicks.
*   **Unused `converted` Flag:** The `converted` column in the `P3AffiliateClick` model (`core/models.py:496`) is defined to track when a user reaches the partner site. However, it is never updated from its default of `0`. The click is logged, but the 'conversion' (as defined in the GOSPEL DB spec) is not.
*   **MAB Threshold Mismatch:** The code at `services/affiliate_injector.py:172` begins applying Thompson Sampling weights after 100 *impressions*. The `PHASE0_ADDENDUM.md` specifies this should happen after 100 *clicks*, which are a much stronger signal of user interest.

### SECTION 2: LAW COMPLIANCE

*   **LAW 1: Contextual relevance only**: **COMPLIANT**. The code uses a combination of AI classification and tag-based filtering (`affiliate_injector.py:306-329`) to ensure CTAs are only shown on relevant articles. It correctly excludes breaking news and prevents both CTAs from appearing on the same page.
*   **LAW 2: A/B test every CTA variant**: **PARTIAL**. The system correctly sets up an A/B test framework based on a user hash and stores outcomes. However, the flawed attribution logic on the landing pages (as noted in Correctness) constitutes a significant violation. It corrupts the A/B test data by misattributing all landing page click-throughs to variant B, making it impossible to evaluate the true winner.
*   **LAW 3: Click tracking hashes IPs**: **COMPLIANT**. The implementation at `services/affiliate_injector.py:335-337` correctly performs a `SHA256` hash of `ip + date + salt` and pulls the salt from an environment variable. Raw IPs are never stored.
*   **LAW 4: Editorial voice**: **COMPLIANT**. The landing page templates (`bitcoin_life_insurance.html` and `digital_residency.html`) contain the specified editorial endorsements and clear "Affiliate Partnership" disclaimers. The inline CTA copy is designed to feel natural.

### SECTION 3: SECURITY

*   **SQL Injection:** **SAFE**. All raw SQL queries in `services/affiliate_injector.py` use bound parameters (e.g., `:partner`), effectively preventing SQL injection vulnerabilities.
*   **Authentication Bypasses:** The admin route `/admin/affiliates` is specified, but its controller is not provided. It is assumed to be protected by an existing admin authentication middleware, but this cannot be verified from the provided code.
*   **Rate Limiting Gaps:** The `/api/affiliates/impression` endpoint is public and appears to lack rate limiting. This endpoint performs a database write. It could be abused by a malicious actor to flood the `p3_affiliate_ab_results` table with bogus impressions, polluting A/B test data and causing unnecessary database load.
*   **Secrets in Code:** **SAFE**. All secrets (API keys, tracking salt) are correctly fetched from environment variables. There are no hardcoded secrets.
*   **Unvalidated User Input:** The `referrer_page` is taken from client-side data and stored. While it doesn't appear to be rendered anywhere without escaping, this is a vector for storing potentially malicious strings in the database.

### SECTION 4: FRONTEND QUALITY

*   **UI Match:** **EXCELLENT**. The admin dashboard and landing pages are visually polished, professional, and adhere closely to the design specifications in the GOSPEL. The typography, co

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main user flow walkthrough

#### 1) Article page loads → CTA decision
The intended flow is: article detail route calls `inject_affiliate_cta(...)`, which classifies content, checks tags/category, assigns a variant, and returns CTA HTML.

**What works**
- `inject_affiliate_cta()` does block obvious breaking-news categories via `if "breaking" in cat_lower` at `services/affiliate_injector.py:305-308`.
- It uses Claude with timeout and fallback keyword classification at `81-143`.
- It ensures only one partner is returned by tie-breaking at `325-327`.

**What is wrong**
1. **LAW mismatch: tag gating is not enforced strictly.**  
   The spec says Meanwhile CTA only on articles tagged wealth/insurance/sovereignty/estate-planning, and RNS only on regulation/privacy/sovereignty/residency/global.  
   But the code allows AI classification alone to trigger a CTA even if tags don’t match. See `317-324`: tags are only a fallback if AI says no. That means an untagged article can still get a CTA. This is a correctness and law issue.

2. **Breaking-news detection is too weak.**  
   It only checks `article_category`, not tags/title/content/flags. `305-308`. If breaking news is tagged `breaking-news` in `article.tags` but category is “Markets”, CTA still appears.

3. **A/B assignment is not what the law says.**  
   `_get_ab_variant()` uses deterministic hash of `user_hash` and partner at `215-225`, but `user_hash` itself is derived from IP+date+salt at `334-338`. That gives consistency per day, not per session. The law says “per user session (based on hash of IP+date, not localStorage)”; arguable, but this implementation is really per-day, not per-session.

4. **Default salt silently weakens privacy guarantees.**  
   `TRACKING_SALT` falls back to hardcoded `"pp-affiliate-default-salt-2026"` at `335`. If env is missing, all installs share the same salt. That violates the intended privacy model and makes hashes predictable across environments.

#### 2) CTA renders in article template
`core/templates/article_detail.html:220-230` renders CTA block hidden with `opacity:0`.

**What works**
- CTA is only rendered if `affiliate_cta` exists.
- JS intent gating attempts to reveal CTA after engagement.

**What is wrong**
1. **JS-disabled fallback is broken.**  
   The addendum says fallback should show CTA at page load if JS disabled. Instead, the CTA container is inline-styled `opacity:0` at `227`, and there is no `<noscript>` override. With JS disabled, CTA is permanently invisible.

2. **CTA is appended after article body, not embedded naturally in article text.**  
   The law/spec says embedded in article text should read naturally. Here it is always a block after the article body at `220-230`, not injected into prose.

3. **Potential malformed click URL mutation.**  
   In `649-656`, click handler appends `?ref=...&v=...` or `&ref=...&v=...`. If link already contains a trailing `?` or `&`, or existing `ref`/`v`, it duplicates params. Not fatal, but sloppy.

4. **Impression tracking can double-fire.**  
   `showCta()` sends beacon once because of `ctaShown`, good. But landing pages separately misuse impression endpoint for click-ish events (see below), polluting metrics.

#### 3) User clicks CTA → redirect tracking
Expected flow: click goes to `/go/meanwhile` or `/go/rns`, server logs click with hashed IP and variant, redirects to partner.

**Problem**
- Those route implementations are **not present in the audit package**. The spec references them in GOSPEL, templates link to them, and helper functions exist, but no route code is shown. So the core click flow cannot be verified end-to-end.
- Because route code is missing, we cannot confirm:
  - raw IP isn’t stored
  - admin auth is enforced
  - redirect URL/referral code is correct
  - click writes and redirect happen atomically enough
  - variant assignment is stored correctly

That is a major audit gap.

#### 4) Impression tracking
`track_impression()` at `399-407` just increments aggregate A/B impressions.

**What is wrong**
1. **No per-user/session impression record.**  
   Law 2 says “Store variant assignment + click outcome in affiliate_clicks table.” Current click table only stores clicks, not impressions/assignments for non-clickers. `P3AffiliateClick` at `489-500` has no impression event rows. Aggregate table alone is insufficient to reconstruct assignment history.

2. **Race condition / lost updates risk.**  
   `_increment_ab_impressions()` and `_increment_ab_clicks()` do `SELECT` then `UPDATE/INSERT` at `415-440` and `447-472`. Under concurrent requests, two workers can both see no row and both try to insert, causing unique constraint errors or lost increments. SQLite under load will expose this.

3. **Click path can inflate impressions incorrectly.**  
   In landing pages, `trackAffClick()` sends a beacon to `/api/affiliates/impression` on click at:
   - `bitcoin_life_insurance.html:608-617`
   - `digital_residency.html:630-638`
   
  

## CLAUDE'S CYCLE 1 CONSENSUS
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
**What to change:** Confirm the route is decorated with the project's admin auth guard. The dec

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: GOSPEL.md (186 lines)
```
   1 | # MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
   2 | # Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.
   3 | 
   4 | # PROTOCOL PULSE — GOSPEL: P3 AFFILIATE INTEGRATION
   5 | # Branch: feature/p3-affiliates | Created: 2026-03-09
   6 | 
   7 | ---
   8 | 
   9 | ## WHAT THIS IS
  10 | Passive revenue from two partner programs:
  11 | - Meanwhile Bitcoin Life Insurance — referralCode=KKM73K
  12 | - RNS.ID Palau Digital Residency — $300/referral
  13 | 
  14 | Includes: landing pages, AI-powered contextual injection on articles,
  15 | click tracking, A/B testing framework, conversion analytics.
  16 | 
  17 | ## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY)
  18 | Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-affiliates --phase0
  19 | Ask all 3 LLMs: "What are the most effective affiliate marketing techniques for a
  20 | premium Bitcoin media audience in 2026? What makes CTAs convert without feeling
  21 | spammy or breaking trust with a cypherpunk-adjacent audience?"
  22 | Incorporate top P0 ideas before building.
  23 | 
  24 | ## THE LAWS
  25 | ### LAW 1: Contextual relevance only — no random banner spam
  26 | Claude Haiku analyzes article content → decides if this article warrants an affiliate CTA
  27 | Meanwhile CTA: only on articles tagged wealth/insurance/sovereignty/estate-planning
  28 | RNS.ID CTA: only on articles tagged regulation/privacy/sovereignty/residency/global
  29 | Never show both CTAs on same article. Never show CTAs on breaking news articles.
  30 | 
  31 | ### LAW 2: A/B test every CTA variant
  32 | 50/50 random split per user session (based on hash of IP+date, not localStorage)
  33 | Variant A: text-only subtle mention
  34 | Variant B: visual card with image/icon
  35 | Track separately. After 200 clicks per variant: evaluate winner, keep winner.
  36 | Store variant assignment + click outcome in affiliate_clicks table.
  37 | 
  38 | ### LAW 3: Click tracking hashes IPs — never store raw
  39 | SHA256(ip + date + salt) → user_hash. Salt = random 32-byte value in .env as TRACKING_SALT.
  40 | Never store: raw IPs, cookies, user IDs. Privacy-first.
  41 | 
  42 | ### LAW 4: Editorial voice — never feel like ads
  43 | Meanwhile landing page: PBX-voice editorial (Matty Ice tone) — "why I trust Meanwhile"
  44 | RNS.ID landing page: Protocol Pulse endorsement — "digital sovereignty starts with ID"
  45 | Both pages have clear disclaimers: "Paid affiliate partnership."
  46 | CTAs embedded in article text should read naturally: "...which is why tools like Meanwhile..."
  47 | 
  48 | ## ARCHITECTURE
  49 | 
  50 | ### Database
  51 | ```sql
  52 | CREATE TABLE IF NOT EXISTS affiliate_clicks (
  53 |   id INTEGER PRIMARY KEY AUTOINCREMENT,
  54 |   partner TEXT NOT NULL,             -- meanwhile|rns_id
  55 |   referrer_page TEXT,                -- /articles/123, /mining, etc.
  56 |   ab_variant TEXT,                   -- A|B
  57 |   converted INTEGER DEFAULT 0,       -- 1 if they reached partner site (redirect tracked)
  58 |   user_hash TEXT,                    -- SHA256(ip+date+salt)
  59 |   user_agent_hash TEXT,              -- SHA256(user_agent)
  60 |   clicked_at DATETIME DEFAULT CURRENT_TIMESTAMP
  61 | );
  62 | 
  63 | CREATE TABLE IF NOT EXISTS affiliate_ab_results (
  64 |   id INTEGER PRIMARY KEY AUTOINCREMENT,
  65 |   partner TEXT NOT NULL,
  66 |   variant TEXT NOT NULL,
  67 |   impressions INTEGER DEFAULT 0,
  68 |   clicks INTEGER DEFAULT 0,
  69 |   calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  70 | );
  71 | 
  72 | CREATE INDEX IF NOT EXISTS idx_aff_partner_date ON affiliate_clicks(partner, clicked_at);
  73 | ```
  74 | 
  75 | ### Routes
  76 | ```python
  77 | GET  /go/meanwhile              → track click → redirect to Meanwhile with referral code
  78 | GET  /go/rns                    → track click → redirect to RNS.ID with referral code
  79 | GET  /bitcoin-life-insurance    → Meanwhile landing page
  80 | GET  /digital-residency         → RNS.ID landing page
  81 | GET  /admin/affiliates          → admin analytics dashboard
  82 | GET  /api/affiliates/metrics    → JSON: clicks/day, conversion rate, top pages
  83 | POST /api/affiliates/impression → track impression (JS beacon call on page load)
  84 | ```
  85 | 
  86 | ### AI Contextual Injection — services/affiliate_injector.py
  87 | inject_affiliate_cta(article_id, article_content) → Optional[dict]:
  88 |   1. Use claude-haiku-4-5 to classify article tags/themes
  89 |   2. Check: does this article qualify for Meanwhile? for RNS.ID?
  90 |   3. If yes: determine A/B variant (hash-based, no session/cookie needed)
  91 |   4. Return: {partner, variant, cta_html} or None
  92 | 
  93 |   Called by: article_detail route (articles/{id}) — inject into template context
  94 |   CTA is NEVER shown more than once per article. NEVER on homepage/list pages.
  95 |   Only on dedicated article view pages.
  96 | 
  97 | ### Meanwhile Landing Page — /bitcoin-life-insurance
  98 | template: bitcoin_life_insurance.html
  99 | 
 100 | DESIGN: Dark, sophisticated, wealth-focused. Black + deep navy + gold accents.
 101 | 
 102 | SECTIONS:
 103 | Hero: "Your Bitcoin Legacy Deserves Protection"
 104 |   Subhead: "Life insurance denominated in Bitcoin — not fiat. Not stocks. Bitcoin."
 105 |   CTA: "Get Your Quote →" (red button, tracks click)
 106 | 
 107 | Why It Matters (3 cards):
 108 |   "Death benefit in BTC — your family inherits sovereignty, not a check"
 109 |   "No fiat conversion risk — benefit doesn't lose purchasing power"
 110 |   "Self-sovereign planning — outside the traditional insurance industry"
 111 | 
 112 | How Meanwhile Works:
 113 |   Whole life product. BTC-denominated policy. Issued by regulated insurer.
 114 |   Application online. Benefit paid in BTC directly to wallet.
 115 | 
 116 | Editorial Section — "Why Protocol Pulse Partners With Meanwhile":
 117 |   Matty Ice/PBX first-person voice. 3 paragraphs. Authentic endorsement.
 118 |   Not a paid ad disguised as editorial — clearly labeled "Affiliate Partnership"
 119 |   but written with genuine Protocol Pulse voice.
 120 | 
 121 | FAQ (6 questions):
 122 |   "Who is Meanwhile?" / "Is this regulated?" / "How is the benefit paid?"
 123 |   "What happens to the BTC if price drops?" / "Is there a medical exam?"
 124 |   "What coverage amounts are available?"
 125 | 
 126 | CTA Footer: "Start Your Application" → /go/meanwhile
 127 | 
 128 | Disclaimer: "Protocol Pulse may earn compensation when you apply through our link.
 129 | This is not financial advice."
 130 | 
 131 | ### RNS.ID Landing Page — /digital-residency
 132 | template: digital_residency.html
 133 | 
 134 | DESIGN: Dark, global, freedom-focused. Black + deep blue + green accents.
 135 | Think: passport aesthetic, global citizen, sovereignty signal.
 136 | 
 137 | SECTIONS:
 138 | Hero: "Establish Your Digital Sovereignty — Palau Digital Residency"
 139 |   Subhead: "A government-issued digital ID outside the traditional financial surveillance state."
 140 |   CTA: "Apply Now →" (green button, tracks click)
 141 | 
 142 | What Is Palau Digital Residency?
 143 |   Official digital identity issued by the Republic of Palau
 144 |   Not crypto — real government-backed digital resident status
 145 |   Enables: international banking access, digital identity verification, mobility
 146 | 
 147 | Why Bitcoiners Care (4 points):
 148 |   Bitcoin-friendly jurisdiction | Tax optimization potential
 149 |   Privacy from surveillance finance | Geographic diversification of identity
 150 | 
 151 | Protocol Pulse endorsement: cypherpunk angle, sovereignty angle, PBX voice
 152 | Disclaimer: "Affiliate partnership."
 153 | 
 154 | FAQ: 5 questions covering legitimacy, banking, tax implications, process
 155 | 
 156 | CTA: "Apply for Digital Residency →" → /go/rns
 157 | 
 158 | ### Admin Analytics — /admin/affiliates
 159 | Dashboard with:
 160 | - Summary: total clicks (30d), meanwhile clicks, rns clicks, estimated earnings
 161 | - Clicks per day chart (Canvas, last 30 days, both partners)
 162 | - Top referrer pages (which articles/pages drive most clicks)
 163 | - A/B test results: variant A vs B click rates per partner, statistical significance
 164 | - "Declare winner" button: locks in winning variant permanently
 165 | 
 166 | ### CTA Variants
 167 | Variant A (text/inline):
 168 |   "Tools like <a href="/bitcoin-life-insurance">Meanwhile</a> let Bitcoiners
 169 |    protect generational wealth with BTC-denominated life insurance."
 170 | 
 171 | Variant B (card):
 172 |   Dark glass card, left red border, Meanwhile logo (text), 2-line pitch, "Learn More →"
 173 | 
 174 | ## VERIFICATION
 175 | - [ ] GET /bitcoin-life-insurance → HTTP 200, editorial content loads
 176 | - [ ] GET /digital-residency → HTTP 200, editorial content loads
 177 | - [ ] GET /go/meanwhile → click logged to DB, redirects with referral code
 178 | - [ ] GET /go/rns → click logged to DB, redirects with referral code
 179 | - [ ] inject_affiliate_cta() returns CTA for relevant articles, None for irrelevant
 180 | - [ ] A/B variant assigned consistently for same user
 181 | - [ ] GET /admin/affiliates → shows click analytics
 182 | - [ ] IP is never stored raw (only hash in DB)
 183 | - [ ] Disclaimer present on both landing pages
 184 | - [ ] regression_test.sh: zero FAILs
 185 | - [ ] git commit + push to origin feature/p3-affiliates
 186 | 
```

### File: PHASE0_ADDENDUM.md (73 lines)
```
   1 | # PHASE 0 ADDENDUM — p3-affiliates
   2 | # Created: 2026-03-09
   3 | # Source: C0_SYNTHESIS.md + C0_GEMINI.md + C0_GROK.md
   4 | 
   5 | ## TOP PHASE 0 SUGGESTIONS TO IMPLEMENT
   6 | 
   7 | ### 1. Thompson Sampling MAB (Multi-Armed Bandit) — IMPLEMENTING
   8 | **What:** Replace static 50/50 split with adaptive traffic allocation after sufficient data
   9 | **How:**
  10 | - `p3_affiliate_ab_results` table stores alpha/beta params for Thompson Sampling
  11 | - Variant selection: deterministic hash of (IP+date+salt) maps into MAB-weighted bucket
  12 | - After 100 clicks per partner: Thompson Sampling weights update automatically
  13 | - Starts 50/50, converges to winner over time
  14 | - "Declare winner" button freezes allocation permanently
  15 | - `_get_ab_variant(partner, user_hash)` in affiliate_injector.py implements this
  16 | 
  17 | ### 2. Client-Side Behavioral Intent Scoring — IMPLEMENTING (lightweight JS, no TF.js)
  18 | **What:** Track scroll depth + time-on-page to score user intent before showing CTA
  19 | **How:**
  20 | - Pure vanilla JS in article_detail.html
  21 | - Tracks: scroll depth (0-100%), time on page (seconds), mouse movement
  22 | - Generates intent score 0-100: (scroll_depth * 0.6 + min(time_secs/120, 1)*40)
  23 | - CTA only injects via JS reveal when intent_score >= 40 (configurable threshold)
  24 | - No TF.js / no external ML - privacy-safe, pure math
  25 | - Falls back to showing CTA at page load if JS disabled
  26 | 
  27 | ### 3. navigator.sendBeacon for Impressions — IMPLEMENTING
  28 | **What:** Non-blocking async impression tracking that doesn't delay page transitions
  29 | **How:**
  30 | - `window.addEventListener('beforeunload', ...)` fires sendBeacon to /api/affiliates/impression
  31 | - Also fires on CTA visibility (IntersectionObserver)
  32 | - Server endpoint handles beacon asynchronously
  33 | 
  34 | ### 4. Statistical Significance Display — IMPLEMENTING
  35 | **What:** Admin dashboard shows p-value and confidence interval for A/B tests
  36 | **How:**
  37 | - Python: scipy-style z-test for two proportions (manual math, no scipy dep)
  38 | - Formula: z = (p1-p2) / sqrt(pooled*(1-pooled)*(1/n1+1/n2))
  39 | - p-value approximated via error function
  40 | - Shows: "95% confidence: Variant A wins" or "Need more data (N=47/200)"
  41 | 
  42 | ### 5. Content-to-Conversion Intelligence in Admin — IMPLEMENTING
  43 | **What:** Show which articles drive most conversions with per-article revenue estimates
  44 | **How:**
  45 | - Admin dashboard: "Top referrer pages" table with clicks + estimated revenue
  46 | - Meanwhile: $150 average commission per funded policy (conservative)
  47 | - RNS.ID: $300 per referral (stated in gospel)
  48 | - Shows: estimated earnings per article, per day
  49 | 
  50 | ### 6. Sovereignty Score Widget on Landing Pages — IMPLEMENTING
  51 | **What:** Visual trust score showing why Protocol Pulse endorses each partner
  52 | **How:**
  53 | - Static widget with 5 criteria: Privacy, Non-custodial, BTC-native, Regulatory, Transparency
  54 | - Score 0-5 bars, gold fill, visible on both landing pages
  55 | - Reinforces trust with cypherpunk audience
  56 | 
  57 | ### 7. k-Anonymity Constraint on Analytics — IMPLEMENTING
  58 | **What:** Never display analytics for fewer than k=10 distinct user hashes
  59 | **How:**
  60 | - All admin analytics queries check count(distinct user_hash) >= 10 before returning
  61 | - For small counts: show "< 10 users — aggregating for privacy" placeholder
  62 | - Implemented in /api/affiliates/metrics endpoint
  63 | 
  64 | ## NOT IMPLEMENTING (over-engineered for this Flask/SQLite env):
  65 | - WebSocket live dashboard → SSE (simpler, same effect, no Redis needed)
  66 | - Edge computing / Cloudflare Workers → not applicable to this Flask stack
  67 | - Redis for MAB storage → SQLite handles MAB state fine at this scale
  68 | - TensorFlow.js behavioral ML → simple scroll/time math is sufficient
  69 | - Blockchain referral tracking → misaligned with simplicity requirement
  70 | - WebXR experiences → banned by GOSPEL (CSS animations only, no 3D)
  71 | - LangChain agent swarms → overkill, Claude Haiku API call is sufficient
  72 | - Voice-activated CTAs → novelty without conversion value
  73 | 
```

### File: core/models.py (974 lines)
```
   1 | from datetime import datetime, timedelta
   2 | from flask_login import UserMixin
   3 | from werkzeug.security import generate_password_hash, check_password_hash
   4 | from app import db  # This stays here; we will fix the 'loop' in app.py
   5 | 
   6 | # =====================================
   7 | # USER & OPERATIVE MODELS
   8 | # =====================================
   9 | 
  10 | class User(UserMixin, db.Model):
  11 |     id = db.Column(db.Integer, primary_key=True)
  12 |     username = db.Column(db.String(80), unique=True, nullable=False)
  13 |     email = db.Column(db.String(120), unique=True, nullable=False)
  14 |     password_hash = db.Column(db.String(256))
  15 |     is_admin = db.Column(db.Boolean, default=False)
  16 |     newsletter_subscribed = db.Column(db.Boolean, default=False)
  17 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
  18 |     
  19 |     operative_rank = db.Column(db.Integer, default=1)
  20 |     drill_completions = db.Column(db.Integer, default=0)
  21 |     brief_clicks = db.Column(db.Integer, default=0)
  22 |     operative_slug = db.Column(db.String(100), unique=True)
  23 |     crm_synced_at = db.Column(db.DateTime)
  24 |     last_drill_at = db.Column(db.DateTime)
  25 |     last_brief_at = db.Column(db.DateTime)
  26 |     
  27 |     # Premium subscription (free | operator | commander | sovereign)
  28 |     subscription_tier = db.Column(db.String(30), default='free')
  29 |     stripe_customer_id = db.Column(db.String(120))
  30 |     stripe_subscription_id = db.Column(db.String(120))
  31 |     subscription_expires_at = db.Column(db.DateTime)
  32 |     # Commander+: opt-in to email alerts for mega whales (≥1000 BTC)
  33 |     mega_whale_email_alerts = db.Column(db.Boolean, default=False)
  34 |     
  35 |     # --- Auth Methods ---
  36 |     def set_password(self, password):
  37 |         self.password_hash = generate_password_hash(password)
  38 | 
  39 |     def check_password(self, password):
  40 |         return check_password_hash(self.password_hash, password)
  41 | 
  42 |     # --- Operative Logic ---
  43 |     def get_rank_name(self):
  44 |         if self.operative_rank >= 3:
  45 |             return 'SOVEREIGN ELITE'
  46 |         elif self.operative_rank >= 2:
  47 |             return 'OPERATIVE'
  48 |         return 'RECRUIT'
  49 |     
  50 |     def check_rank_progression(self):
  51 |         if self.drill_completions >= 5 and self.brief_clicks >= 10:
  52 |             self.operative_rank = 3
  53 |         elif self.drill_completions >= 1:
  54 |             self.operative_rank = 2
  55 |         else:
  56 |             self.operative_rank = 1
  57 |     
  58 |     def generate_operative_slug(self):
  59 |         import hashlib
  60 |         import time
  61 |         if not self.operative_slug:
  62 |             base = self.username.lower().replace(' ', '-')[:20]
  63 |             unique_hash = hashlib.md5(f"{self.email}{time.time()}".encode()).hexdigest()[:6]
  64 |             self.operative_slug = f"{base}-{unique_hash}"
  65 |         return self.operative_slug
  66 |     
  67 |     def can_increment_drill(self):
  68 |         if not self.last_drill_at:
  69 |             return True
  70 |         cooldown = datetime.utcnow() - self.last_drill_at
  71 |         return cooldown.total_seconds() >= 300
  72 |     
  73 |     def can_increment_brief(self):
  74 |         if not self.last_brief_at:
  75 |             return True
  76 |         cooldown = datetime.utcnow() - self.last_brief_at
  77 |         return cooldown.total_seconds() >= 60
  78 |     
  79 |     def has_premium(self):
  80 |         """True if user has any paid tier (operator, commander, sovereign)."""
  81 |         tier = getattr(self, 'subscription_tier', None)
  82 |         return tier and tier != 'free'
  83 | 
  84 |     def has_commander_tier(self):
  85 |         """True if user has $99/mo Commander (or higher) tier."""
  86 |         tier = getattr(self, 'subscription_tier', None)
  87 |         return tier in ('commander', 'sovereign')
  88 | 
  89 | # =====================================
  90 | # CONTENT & INTELLIGENCE MODELS
  91 | # =====================================
  92 | 
  93 | class Article(db.Model):
  94 |     __tablename__ = "articles"
  95 |     id = db.Column(db.Integer, primary_key=True)
  96 |     title = db.Column(db.String(200), nullable=False)
  97 |     content = db.Column(db.Text, nullable=False)
  98 |     summary = db.Column(db.Text)
  99 |     author = db.Column(db.String(100), default="Protocol Pulse AI")
 100 |     category = db.Column(db.String(50), default="Web3")
 101 |     tags = db.Column(db.String(500))
 102 |     source_url = db.Column(db.String(500))
 103 |     source_type = db.Column(db.String(50))
 104 |     featured = db.Column(db.Boolean, default=False)
 105 |     published = db.Column(db.Boolean, default=False)
 106 |     # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
 107 |     premium_tier = db.Column(db.String(30), default=None)
 108 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 109 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 110 |     seo_title = db.Column(db.String(200))
 111 |     seo_description = db.Column(db.String(300))
 112 |     substack_url = db.Column(db.String(500))
 113 |     header_image_url = db.Column(db.String(500))
 114 |     screenshot_url = db.Column(db.String(500))
 115 |     video_url = db.Column(db.String(500))
 116 | 
 117 | class Podcast(db.Model):
 118 |     id = db.Column(db.Integer, primary_key=True)
 119 |     title = db.Column(db.String(200), nullable=False)
 120 |     description = db.Column(db.Text)
 121 |     host = db.Column(db.String(100))
 122 |     episode_number = db.Column(db.Integer)
 123 |     duration = db.Column(db.String(20))
 124 |     audio_url = db.Column(db.String(500))
 125 |     cover_image_url = db.Column(db.String(500))
 126 |     published_date = db.Column(db.DateTime, default=datetime.utcnow)
 127 |     featured = db.Column(db.Boolean, default=False)
 128 |     category = db.Column(db.String(50), default="Web3")
 129 |     rss_source = db.Column(db.String(100))
 130 | 
 131 | class ContentPrompt(db.Model):
 132 |     id = db.Column(db.Integer, primary_key=True)
 133 |     name = db.Column(db.String(100), nullable=False)
 134 |     prompt_text = db.Column(db.Text, nullable=False)
 135 |     category = db.Column(db.String(50))
 136 |     active = db.Column(db.Boolean, default=True)
 137 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 138 | 
 139 | class Advertisement(db.Model):
 140 |     id = db.Column(db.Integer, primary_key=True)
 141 |     name = db.Column(db.String(150), nullable=False)
 142 |     image_url = db.Column(db.String(300), nullable=False)
 143 |     target_url = db.Column(db.String(300), nullable=False)
 144 |     is_active = db.Column(db.Boolean, default=False)
 145 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 146 | 
 147 | 
 148 | class AffiliateProduct(db.Model):
 149 |     """Products we have affiliate links for (Amazon, Trezor, etc.) — used in product-highlight articles."""
 150 |     __tablename__ = 'affiliate_product'
 151 |     id = db.Column(db.Integer, primary_key=True)
 152 |     name = db.Column(db.String(200), nullable=False)
 153 |     product_type = db.Column(db.String(50), nullable=False)  # amazon_book, trezor, cold_wallet, seed_plate, miner, etc.
 154 |     product_id = db.Column(db.String(100))  # ASIN, offer_id, etc.
 155 |     affiliate_url = db.Column(db.String(500))
 156 |     category = db.Column(db.String(80))  # cold_wallet, seed_plate, bitaxe_miner, book, etc.
 157 |     short_description = db.Column(db.String(500))
 158 |     active = db.Column(db.Boolean, default=True)
 159 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 160 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 161 | 
 162 | 
 163 | class AffiliateProductClick(db.Model):
 164 |     """Track affiliate product link clicks for revenue analytics (Smart Analytics)."""
 165 |     __tablename__ = 'affiliate_product_click'
 166 |     id = db.Column(db.Integer, primary_key=True)
 167 |     product_id = db.Column(db.Integer, db.ForeignKey('affiliate_product.id'), nullable=True)
 168 |     link_type = db.Column(db.String(50))  # amazon, trezor, etc.
 169 |     page_path = db.Column(db.String(500))
 170 |     session_id = db.Column(db.String(64))
 171 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 172 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 173 | 
 174 | 
 175 | # =====================================
 176 | # AUTOMATION & LOGISTICS
 177 | # =====================================
 178 | 
 179 | class AutomationRun(db.Model):
 180 |     id = db.Column(db.Integer, primary_key=True)
 181 |     task_name = db.Column(db.String(100), nullable=False)
 182 |     started_at = db.Column(db.DateTime, nullable=False)
 183 |     finished_at = db.Column(db.DateTime)
 184 |     status = db.Column(db.String(20))
 185 |     error = db.Column(db.String(500))
 186 | 
 187 | class LaunchSequence(db.Model):
 188 |     id = db.Column(db.Integer, primary_key=True)
 189 |     content_id = db.Column(db.Integer)
 190 |     content_type = db.Column(db.String(50))
 191 |     primary_post_copy = db.Column(db.Text)
 192 |     thread_replies = db.Column(db.Text)
 193 |     quote_variants = db.Column(db.Text)
 194 |     reply_drafts = db.Column(db.Text)
 195 |     hashtags = db.Column(db.String(500))
 196 |     posting_time = db.Column(db.Time)
 197 |     velocity_prediction = db.Column(db.Float)
 198 |     first_reply_link = db.Column(db.String(500))
 199 |     call_to_action = db.Column(db.String(300))
 200 |     status = db.Column(db.String(50), default='draft')
 201 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 202 |     approved_at = db.Column(db.DateTime)
 203 |     published_at = db.Column(db.DateTime)
 204 |     tweet_id = db.Column(db.String(100))
 205 |     actual_velocity_score = db.Column(db.Float)
 206 |     replies_first_5min = db.Column(db.Integer, default=0)
 207 |     total_engagement = db.Column(db.Integer, default=0)
 208 |     reached_for_you = db.Column(db.Boolean, default=False)
 209 |     dispatch_window = db.Column(db.String(20))
 210 |     dispatch_timezone = db.Column(db.String(50), default='America/New_York')
 211 |     persona_debate = db.Column(db.Text)
 212 |     is_autonomous = db.Column(db.Boolean, default=False)
 213 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 214 |     ground_truth = db.Column(db.Text)
 215 |     target_segment = db.Column(db.String(100))
 216 |     generated_by = db.Column(db.String(50))
 217 |     nostr_event_id = db.Column(db.String(100))
 218 |     x_tweet_id = db.Column(db.String(100))
 219 |     is_approved = db.Column(db.Boolean, default=False)
 220 |     is_posted = db.Column(db.Boolean, default=False)
 221 | 
 222 | class TargetAlert(db.Model):
 223 |     id = db.Column(db.Integer, primary_key=True)
 224 |     trigger_type = db.Column(db.String(50))
 225 |     source_url = db.Column(db.String(500))
 226 |     source_account = db.Column(db.String(100))
 227 |     content_snippet = db.Column(db.Text)
 228 |     priority = db.Column(db.Integer, default=2)
 229 |     strategy_suggested = db.Column(db.String(100))
 230 |     draft_replies = db.Column(db.Text)
 231 |     status = db.Column(db.String(50), default='pending')
 232 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 233 |     responded_at = db.Column(db.DateTime)
 234 | 
 235 | class NostrEvent(db.Model):
 236 |     id = db.Column(db.Integer, primary_key=True)
 237 |     event_id = db.Column(db.String(100))
 238 |     content_type = db.Column(db.String(50))
 239 |     content_id = db.Column(db.Integer)
 240 |     relays_success = db.Column(db.Text)
 241 |     relays_failed = db.Column(db.Text)
 242 |     zaps_received = db.Column(db.Integer, default=0)
 243 |     zaps_amount_sats = db.Column(db.Integer, default=0)
 244 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 245 | 
 246 | class ReplySquadMember(db.Model):
 247 |     id = db.Column(db.Integer, primary_key=True)
 248 |     handle = db.Column(db.String(100), nullable=False)
 249 |     display_name = db.Column(db.String(150))
 250 |     category = db.Column(db.String(100))
 251 |     priority = db.Column(db.Integer, default=2)
 252 |     reciprocal_engagements = db.Column(db.Integer, default=0)
 253 |     last_engagement = db.Column(db.DateTime)
 254 |     notes = db.Column(db.Text)
 255 |     active = db.Column(db.Boolean, default=True)
 256 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 257 | 
 258 | # =====================================
 259 | # BITCOIN NETWORK & DONATIONS
 260 | # =====================================
 261 | 
 262 | class WhaleTransaction(db.Model):
 263 |     id = db.Column(db.Integer, primary_key=True)
 264 |     txid = db.Column(db.String(100), unique=True, nullable=False)
 265 |     btc_amount = db.Column(db.Float, nullable=False)
 266 |     usd_value = db.Column(db.Float)
 267 |     fee_sats = db.Column(db.Integer)
 268 |     block_height = db.Column(db.Integer)
 269 |     detected_at = db.Column(db.DateTime, default=datetime.utcnow)
 270 |     is_mega = db.Column(db.Boolean, default=False)
 271 | 
 272 | 
 273 | class ContactSubmission(db.Model):
 274 |     """Contact form submissions (stored for admin; optional email notification)."""
 275 |     id = db.Column(db.Integer, primary_key=True)
 276 |     name = db.Column(db.String(200), nullable=False)
 277 |     email = db.Column(db.String(200), nullable=False)
 278 |     subject = db.Column(db.String(100), nullable=False)
 279 |     message = db.Column(db.Text, nullable=False)
 280 |     ip_address = db.Column(db.String(64))
 281 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 282 |     read = db.Column(db.Boolean, default=False)
 283 | 
 284 | 
 285 | class PremiumAsk(db.Model):
 286 |     """Sovereign Elite monthly ask: one research/question per month, answered by team."""
 287 |     id = db.Column(db.Integer, primary_key=True)
 288 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 289 |     question_text = db.Column(db.Text, nullable=False)
 290 |     status = db.Column(db.String(20), default='pending')  # pending | answered
 291 |     answer_text = db.Column(db.Text)
 292 |     answer_url = db.Column(db.String(500))  # optional link to brief or doc
 293 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 294 |     answered_at = db.Column(db.DateTime)
 295 |     user = db.relationship('User', backref=db.backref('premium_asks', lazy='dynamic'))
 296 | 
 297 | 
 298 | class BitcoinDonation(db.Model):
 299 |     id = db.Column(db.Integer, primary_key=True)
 300 |     payment_id = db.Column(db.String(100))
 301 |     amount_sats = db.Column(db.Integer)
 302 |     amount_usd = db.Column(db.Float)
 303 |     donor_email = db.Column(db.String(200))
 304 |     donor_name = db.Column(db.String(200))
 305 |     message = db.Column(db.Text)
 306 |     status = db.Column(db.String(50), default='pending')
 307 |     payment_method = db.Column(db.String(50))
 308 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 309 |     confirmed_at = db.Column(db.DateTime)
 310 | 
 311 | # =====================================
 312 | # ANALYTICS & PERFORMANCE
 313 | # =====================================
 314 | 
 315 | class EngagementEvent(db.Model):
 316 |     id = db.Column(db.Integer, primary_key=True)
 317 |     event_type = db.Column(db.String(50), nullable=False)
 318 |     content_type = db.Column(db.String(50))
 319 |     content_id = db.Column(db.Integer)
 320 |     source_platform = db.Column(db.String(50))
 321 |     source_url = db.Column(db.String(500))
 322 |     persona = db.Column(db.String(50))
 323 |     strategy = db.Column(db.String(100))
 324 |     minutes_after_post = db.Column(db.Float)
 325 |     is_30min_window = db.Column(db.Boolean, default=False)
 326 |     grok_score_contribution = db.Column(db.Integer, default=0)
 327 |     user_agent = db.Column(db.String(300))
 328 |     referrer = db.Column(db.String(500))
 329 |     ip_hash = db.Column(db.String(64))
 330 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 331 | 
 332 | class ContentPerformance(db.Model):
 333 |     id = db.Column(db.Integer, primary_key=True)
 334 |     content_type = db.Column(db.String(50), nullable=False)
 335 |     content_id = db.Column(db.Integer, nullable=False)
 336 |     content_title = db.Column(db.String(300))
 337 |     total_views = db.Column(db.Integer, default=0)
 338 |     total_clicks = db.Column(db.Integer, default=0)
 339 |     total_replies = db.Column(db.Integer, default=0)
 340 |     total_retweets = db.Column(db.Integer, default=0)
 341 |     total_quotes = db.Column(db.Integer, default=0)
 342 |     total_likes = db.Column(db.Integer, default=0)
 343 |     profile_visits = db.Column(db.Integer, default=0)
 344 |     replies_0_5min = db.Column(db.Integer, default=0)
 345 |     replies_5_15min = db.Column(db.Integer, default=0)
 346 |     replies_15_30min = db.Column(db.Integer, default=0)
 347 |     replies_30plus_min = db.Column(db.Integer, default=0)
 348 |     velocity_score = db.Column(db.Float, default=0)
 349 |     grok_score_total = db.Column(db.Integer, default=0)
 350 |     reached_for_you = db.Column(db.Boolean, default=False)
 351 |     peak_velocity_minute = db.Column(db.Integer)
 352 |     alex_engagements = db.Column(db.Integer, default=0)
 353 |     sarah_engagements = db.Column(db.Integer, default=0)
 354 |     best_performing_strategy = db.Column(db.String(100))
 355 |     best_performing_time = db.Column(db.String(20))
 356 |     published_at = db.Column(db.DateTime)
 357 |     last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 358 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 359 | 
 360 | class AnalyticsSummary(db.Model):
 361 |     id = db.Column(db.Integer, primary_key=True)
 362 |     period_type = db.Column(db.String(20), nullable=False)
 363 |     period_start = db.Column(db.Date, nullable=False)
 364 |     period_end = db.Column(db.Date, nullable=False)
 365 |     total_posts = db.Column(db.Integer, default=0)
 366 |     total_impressions = db.Column(db.Integer, default=0)
 367 |     total_engagements = db.Column(db.Integer, default=0)
 368 |     total_profile_visits = db.Column(db.Integer, default=0)
 369 |     total_followers_gained = db.Column(db.Integer, default=0)
 370 |     avg_velocity_score = db.Column(db.Float, default=0)
 371 |     avg_grok_score = db.Column(db.Float, default=0)
 372 |     for_you_reach_rate = db.Column(db.Float, default=0)
 373 |     top_performing_content_id = db.Column(db.Integer)
 374 |     top_performing_content_type = db.Column(db.String(50))
 375 |     top_performing_strategy = db.Column(db.String(100))
 376 |     alex_total_score = db.Column(db.Integer, default=0)
 377 |     sarah_total_score = db.Column(db.Integer, default=0)
 378 |     persona_winner = db.Column(db.String(50))
 379 |     best_posting_hour = db.Column(db.Integer)
 380 |     best_posting_day = db.Column(db.Integer)
 381 |     sponsor_value_estimate = db.Column(db.Float)
 382 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 383 | 
 384 | class Sponsor(db.Model):
 385 |     id = db.Column(db.Integer, primary_key=True)
 386 |     name = db.Column(db.String(200), nullable=False)
 387 |     company = db.Column(db.String(200))
 388 |     email = db.Column(db.String(200))
 389 |     website_url = db.Column(db.String(500))
 390 |     logo_url = db.Column(db.String(500))
 391 |     tier = db.Column(db.String(50), default='standard')
 392 |     status = db.Column(db.String(50), default='pending')
 393 |     impressions = db.Column(db.Integer, default=0)
 394 |     clicks = db.Column(db.Integer, default=0)
 395 |     ctr = db.Column(db.Float, default=0)
 396 |     budget_sats = db.Column(db.Integer, default=0)
 397 |     spent_sats = db.Column(db.Integer, default=0)
 398 |     cpm_sats = db.Column(db.Integer, default=1000)
 399 |     target_categories = db.Column(db.String(500))
 400 |     target_personas = db.Column(db.String(200))
 401 |     ad_copy = db.Column(db.Text)
 402 |     cta_text = db.Column(db.String(100))
 403 |     cta_url = db.Column(db.String(500))
 404 |     start_date = db.Column(db.DateTime)
 405 |     end_date = db.Column(db.DateTime)
 406 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 407 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 408 | 
 409 | class CreditAccount(db.Model):
 410 |     id = db.Column(db.Integer, primary_key=True)
 411 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 412 |     signal_points = db.Column(db.Integer, default=0)
 413 |     lifetime_points = db.Column(db.Integer, default=0)
 414 |     tier = db.Column(db.String(50), default='recruit')
 415 |     tier_progress = db.Column(db.Float, default=0)
 416 |     articles_read = db.Column(db.Integer, default=0)
 417 |     podcasts_listened = db.Column(db.Integer, default=0)
 418 |     quizzes_completed = db.Column(db.Integer, default=0)
 419 |     referrals_made = db.Column(db.Integer, default=0)
 420 |     streak_days = db.Column(db.Integer, default=0)
 421 |     longest_streak = db.Column(db.Integer, default=0)
 422 |     last_activity = db.Column(db.DateTime)
 423 |     badges = db.Column(db.Text)
 424 |     achievements = db.Column(db.Text)
 425 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 426 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 427 |     user = db.relationship('User', backref=db.backref('credit_account', uselist=False))
 428 | 
 429 | class PredictionOracle(db.Model):
 430 |     id = db.Column(db.Integer, primary_key=True)
 431 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 432 |     prediction_type = db.Column(db.String(50))
 433 |     prediction_value = db.Column(db.Float)
 434 |     target_date = db.Column(db.DateTime)
 435 |     actual_value = db.Column(db.Float)
 436 |     accuracy_score = db.Column(db.Float)
 437 |     status = db.Column(db.String(50), default='pending')
 438 |     is_correct = db.Column(db.Boolean)
 439 |     signal_points_wagered = db.Column(db.Integer, default=0)
 440 |     signal_points_won = db.Column(db.Integer, default=0)
 441 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 442 |     resolved_at = db.Column(db.DateTime)
 443 | 
 444 | class UserSegment(db.Model):
 445 |     id = db.Column(db.Integer, primary_key=True)
 446 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 447 |     segment_type = db.Column(db.String(50), default='general')
 448 |     confidence = db.Column(db.Float, default=0.5)
 449 |     hashrate_interest = db.Column(db.Float, default=0)
 450 |     macro_interest = db.Column(db.Float, default=0)
 451 |     technical_interest = db.Column(db.Float, default=0)
 452 |     trading_interest = db.Column(db.Float, default=0)
 453 |     privacy_interest = db.Column(db.Float, default=0)
 454 |     articles_viewed = db.Column(db.Integer, default=0)
 455 |     avg_read_time = db.Column(db.Float, default=0)
 456 |     preferred_categories = db.Column(db.Text)
 457 |     last_classification = db.Column(db.DateTime, default=datetime.utcnow)
 458 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 459 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 460 |     user = db.relationship('User', backref=db.backref('segment', uselist=False))
 461 | 
 462 | class AffiliatePartner(db.Model):
 463 |     __tablename__ = 'affiliate_partner'
 464 |     id = db.Column(db.Integer, primary_key=True)
 465 |     name = db.Column(db.String(100), unique=True, nullable=False)
 466 |     slug = db.Column(db.String(50), unique=True, nullable=False)
 467 |     category = db.Column(db.String(50))
 468 |     url = db.Column(db.String(500))
 469 |     benefit = db.Column(db.String(200))
 470 |     is_active = db.Column(db.Boolean, default=True)
 471 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 472 |     clicks = db.relationship('AffiliateClick', backref='partner', lazy='dynamic')
 473 | 
 474 | class AffiliateClick(db.Model):
 475 |     __tablename__ = 'affiliate_click'
 476 |     id = db.Column(db.Integer, primary_key=True)
 477 |     partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=False)
 478 |     source_page = db.Column(db.String(500))
 479 |     ip_hash = db.Column(db.String(64))
 480 |     user_agent = db.Column(db.String(500))
 481 |     clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
 482 | 
 483 | 
 484 | # ============================================================
 485 | # P3 AFFILIATE TABLES — Meanwhile + RNS.ID
 486 | # Created: 2026-03-09
 487 | # ============================================================
 488 | 
 489 | class P3AffiliateClick(db.Model):
 490 |     """Privacy-first click tracking for Meanwhile + RNS.ID affiliate programs."""
 491 |     __tablename__ = 'p3_affiliate_clicks'
 492 |     id = db.Column(db.Integer, primary_key=True)
 493 |     partner = db.Column(db.String(50), nullable=False)       # meanwhile | rns_id
 494 |     referrer_page = db.Column(db.String(500))                # /articles/123, etc.
 495 |     ab_variant = db.Column(db.String(1))                     # A | B
 496 |     converted = db.Column(db.Integer, default=0)             # 1 if reached partner site
 497 |     user_hash = db.Column(db.String(64))                     # SHA256(ip+date+salt)
 498 |     user_agent_hash = db.Column(db.String(64))               # SHA256(user_agent)
 499 |     clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
 500 | 
 501 |     __table_args__ = (
 502 |         db.Index('idx_p3_aff_partner_date', 'partner', 'clicked_at'),
 503 |         db.Index('idx_p3_aff_variant', 'partner', 'ab_variant'),
 504 |     )
 505 | 
 506 | 
 507 | class P3AffiliateAbResults(db.Model):
 508 |     """A/B test aggregates for Thompson Sampling MAB."""
 509 |     __tablename__ = 'p3_affiliate_ab_results'
 510 |     id = db.Column(db.Integer, primary_key=True)
 511 |     partner = db.Column(db.String(50), nullable=False)       # meanwhile | rns_id
 512 |     variant = db.Column(db.String(1), nullable=False)        # A | B
 513 |     impressions = db.Column(db.Integer, default=0)
 514 |     clicks = db.Column(db.Integer, default=0)
 515 |     winner_locked = db.Column(db.Boolean, default=False)     # True = MAB frozen
 516 |     calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
 517 | 
 518 |     __table_args__ = (
 519 |         db.UniqueConstraint('partner', 'variant', name='uq_p3_ab_partner_variant'),
 520 |     )
 521 | 
 522 | 
 523 | class FeedItem(db.Model):
 524 |     __tablename__ = 'feed_item'
 525 |     id = db.Column(db.Integer, primary_key=True)
 526 |     source = db.Column(db.String(100), nullable=False)
 527 |     source_type = db.Column(db.String(50), nullable=False)
 528 |     tier = db.Column(db.String(20))
 529 |     title = db.Column(db.String(500))
 530 |     url = db.Column(db.String(1000), unique=True)
 531 |     published_at = db.Column(db.DateTime)
 532 |     author = db.Column(db.String(100))
 533 |     summary = db.Column(db.Text)
 534 |     platform_icon = db.Column(db.String(50))
 535 |     raw_json = db.Column(db.Text)
 536 |     verified = db.Column(db.Boolean, default=False)
 537 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 538 | 
 539 | class SentimentSnapshot(db.Model):
 540 |     __tablename__ = 'sentiment_snapshot'
 541 |     id = db.Column(db.Integer, primary_key=True)
 542 |     score = db.Column(db.Float, default=50.0)
 543 |     state = db.Column(db.String(50), default='EQUILIBRIUM')
 544 |     state_label = db.Column(db.String(50), default='EQUILIBRIUM')
 545 |     state_color = db.Column(db.String(20), default='#ffffff')
 546 |     velocity = db.Column(db.Float, default=0.0)
 547 |     top_keywords = db.Column(db.Text)
 548 |     top_topics_json = db.Column(db.Text)
 549 |     sample_size = db.Column(db.Integer, default=0)
 550 |     verified_weight = db.Column(db.Integer, default=0)
 551 |     computed_at = db.Column(db.DateTime, default=datetime.utcnow)
 552 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 553 | 
 554 | class PulseEvent(db.Model):
 555 |     __tablename__ = 'pulse_event'
 556 |     id = db.Column(db.Integer, primary_key=True)
 557 |     event_type = db.Column(db.String(50), nullable=False)
 558 |     from_state = db.Column(db.String(50))
 559 |     to_state = db.Column(db.String(50))
 560 |     score = db.Column(db.Float)
 561 |     triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
 562 |     payload_json = db.Column(db.Text)
 563 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 564 | 
 565 | class AutoPostDraft(db.Model):
 566 |     __tablename__ = 'autopost_draft'
 567 |     id = db.Column(db.Integer, primary_key=True)
 568 |     platform = db.Column(db.String(30), nullable=False)
 569 |     status = db.Column(db.String(20), default='draft')
 570 |     body = db.Column(db.Text)
 571 |     reason = db.Column(db.String(200))
 572 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 573 |     approved_at = db.Column(db.DateTime)
 574 |     posted_at = db.Column(db.DateTime)
 575 | 
 576 | class DailyBrief(db.Model):
 577 |     __tablename__ = 'daily_brief'
 578 |     id = db.Column(db.Integer, primary_key=True)
 579 |     headline = db.Column(db.String(500))
 580 |     body = db.Column(db.Text)
 581 |     signals_json = db.Column(db.Text)
 582 |     status = db.Column(db.String(20), default='draft')
 583 |     published_at = db.Column(db.DateTime)
 584 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 585 | 
 586 | class PageView(db.Model):
 587 |     __tablename__ = 'page_view'
 588 |     id = db.Column(db.Integer, primary_key=True)
 589 |     page_path = db.Column(db.String(500), nullable=False)
 590 |     page_title = db.Column(db.String(300))
 591 |     page_category = db.Column(db.String(50))
 592 |     session_id = db.Column(db.String(64))
 593 |     ip_hash = db.Column(db.String(64))
 594 |     user_agent = db.Column(db.String(300))
 595 |     referrer = db.Column(db.String(500))
 596 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 597 |     time_on_page = db.Column(db.Integer, default=0)
 598 |     scroll_depth = db.Column(db.Integer, default=0)
 599 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 600 | 
 601 | class HotMoment(db.Model):
 602 |     __tablename__ = 'hot_moment'
 603 |     id = db.Column(db.Integer, primary_key=True)
 604 |     page_path = db.Column(db.String(500), nullable=False)
 605 |     page_title = db.Column(db.String(300))
 606 |     page_category = db.Column(db.String(50))
 607 |     views_in_window = db.Column(db.Integer, default=0)
 608 |     unique_visitors = db.Column(db.Integer, default=0)
 609 |     heat_score = db.Column(db.Float, default=0)
 610 |     is_peak = db.Column(db.Boolean, default=False)
 611 |     peak_detected_at = db.Column(db.DateTime)
 612 |     tweet_drafted = db.Column(db.Boolean, default=False)
 613 |     tweet_content = db.Column(db.Text)
 614 |     tweet_posted_at = db.Column(db.DateTime)
 615 |     window_start = db.Column(db.DateTime, nullable=False)
 616 |     window_end = db.Column(db.DateTime, nullable=False)
 617 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 618 | 
 619 | class ContentSuggestion(db.Model):
 620 |     __tablename__ = 'content_suggestion'
 621 |     id = db.Column(db.Integer, primary_key=True)
 622 |     suggestion_type = db.Column(db.String(50))
 623 |     title = db.Column(db.String(300))
 624 |     description = db.Column(db.Text)
 625 |     reasoning = db.Column(db.Text)
 626 |     based_on_page = db.Column(db.String(500))
 627 |     based_on_trend = db.Column(db.String(200))
 628 |     confidence_score = db.Column(db.Float, default=0)
 629 |     status = db.Column(db.String(20), default='pending')
 630 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 631 |     actioned_at = db.Column(db.DateTime)
 632 | 
 633 | class AutoTweet(db.Model):
 634 |     __tablename__ = 'auto_tweet'
 635 |     id = db.Column(db.Integer, primary_key=True)
 636 |     trigger_type = db.Column(db.String(50))
 637 |     trigger_page = db.Column(db.String(500))
 638 |     heat_score_at_trigger = db.Column(db.Float)
 639 |     tweet_content = db.Column(db.Text, nullable=False)
 640 |     hashtags = db.Column(db.String(200))
 641 |     status = db.Column(db.String(20), default='draft')
 642 |     approved_at = db.Column(db.DateTime)
 643 |     posted_at = db.Column(db.DateTime)
 644 |     post_url = db.Column(db.String(500))
 645 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 646 | 
 647 | 
 648 | # =====================================
 649 | # X ENGAGEMENT SENTRY (TWEET REPLIES)
 650 | # =====================================
 651 | 
 652 | 
 653 | class XInboxTweet(db.Model):
 654 |     """Incoming tweets from monitored X accounts for Sovereign Sentry."""
 655 |     __tablename__ = 'x_inbox_tweet'
 656 | 
 657 |     id = db.Column(db.Integer, primary_key=True)
 658 |     tweet_id = db.Column(db.String(64), unique=True, nullable=False)
 659 |     author_handle = db.Column(db.String(50), nullable=False, index=True)
 660 |     author_name = db.Column(db.String(100))
 661 |     tweet_text = db.Column(db.Text, nullable=False)
 662 |     tweet_url = db.Column(db.String(500))
 663 |     tweet_created_at = db.Column(db.DateTime)
 664 |     status = db.Column(
 665 |         db.String(20),
 666 |         default='new',
 667 |     )  # new | drafted | approved | posted | rejected | skipped | error
 668 |     tier = db.Column(db.String(30))
 669 |     style = db.Column(db.String(30))
 670 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 671 | 
 672 | 
 673 | class XReplyDraft(db.Model):
 674 |     """Generated reply drafts evaluated by Sovereign Sentry."""
 675 |     __tablename__ = 'x_reply_draft'
 676 | 
 677 |     id = db.Column(db.Integer, primary_key=True)
 678 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 679 |     draft_text = db.Column(db.String(300), nullable=False)
 680 |     confidence = db.Column(db.Float)
 681 |     reasoning = db.Column(db.Text)
 682 |     style_used = db.Column(db.String(30))
 683 |     risk_flags = db.Column(db.Text)  # optional JSON array string
 684 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 685 | 
 686 |     inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))
 687 | 
 688 | 
 689 | class XReplyPost(db.Model):
 690 |     """Log of replies actually posted to X."""
 691 |     __tablename__ = 'x_reply_post'
 692 | 
 693 |     id = db.Column(db.Integer, primary_key=True)
 694 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 695 |     draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
 696 |     reply_tweet_id = db.Column(db.String(64))
 697 |     posted_at = db.Column(db.DateTime, default=datetime.utcnow)
 698 |     response_payload = db.Column(db.Text)  # raw JSON from X API
 699 | 
 700 |     inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
 701 |     draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))
 702 | 
 703 | 
 704 | # =====================================
 705 | # VALUE STREAM MODELS
 706 | # =====================================
 707 | 
 708 | class ValueCreator(db.Model):
 709 |     __tablename__ = 'value_creator'
 710 |     id = db.Column(db.Integer, primary_key=True)
 711 |     display_name = db.Column(db.String(100), nullable=False)
 712 |     nostr_pubkey = db.Column(db.String(128), unique=True)
 713 |     lightning_address = db.Column(db.String(200))
 714 |     nip05 = db.Column(db.String(200))
 715 |     twitter_handle = db.Column(db.String(50))
 716 |     youtube_channel_id = db.Column(db.String(50))
 717 |     reddit_username = db.Column(db.String(50))
 718 |     stacker_news_username = db.Column(db.String(50))
 719 |     profile_image = db.Column(db.String(500))
 720 |     bio = db.Column(db.Text)
 721 |     total_sats_received = db.Column(db.BigInteger, default=0)
 722 |     total_zaps = db.Column(db.Integer, default=0)
 723 |     curator_score = db.Column(db.Float, default=0)
 724 |     verified = db.Column(db.Boolean, default=False)
 725 |     verified_at = db.Column(db.DateTime)
 726 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 727 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 728 |     curated_posts = db.relationship('CuratedPost', backref='creator', lazy='dynamic',
 729 |                                      foreign_keys='CuratedPost.creator_id')
 730 |     submitted_posts = db.relationship('CuratedPost', backref='curator', lazy='dynamic',
 731 |                                        foreign_keys='CuratedPost.curator_id')
 732 | 
 733 | class CuratedPost(db.Model):
 734 |     __tablename__ = 'curated_post'
 735 |     id = db.Column(db.Integer, primary_key=True)
 736 |     platform = db.Column(db.String(30), nullable=False)
 737 |     original_url = db.Column(db.String(1000), nullable=False, unique=True)
 738 |     original_id = db.Column(db.String(200))
 739 |     title = db.Column(db.String(500))
 740 |     content_preview = db.Column(db.Text)
 741 |     thumbnail_url = db.Column(db.String(500))
 742 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 743 |     curator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 744 |     total_sats = db.Column(db.BigInteger, default=0)
 745 |     zap_count = db.Column(db.Integer, default=0)
 746 |     boost_sats = db.Column(db.BigInteger, default=0)
 747 |     signal_score = db.Column(db.Float, default=0)
 748 |     decay_factor = db.Column(db.Float, default=1.0)
 749 |     is_verified = db.Column(db.Boolean, default=False)
 750 |     is_featured = db.Column(db.Boolean, default=False)
 751 |     submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
 752 |     last_zap_at = db.Column(db.DateTime)
 753 |     
 754 |     def calculate_signal_score(self):
 755 |         age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
 756 |         time_decay = max(0.1, 1 - (age_hours / 168))
 757 |         raw_score = (self.total_sats * 0.001) + (self.zap_count * 10)
 758 |         self.signal_score = raw_score * time_decay * self.decay_factor
 759 |         return self.signal_score
 760 | 
 761 | class ZapEvent(db.Model):
 762 |     __tablename__ = 'zap_event'
 763 |     id = db.Column(db.Integer, primary_key=True)
 764 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 765 |     sender_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 766 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 767 |     creator_share = db.Column(db.BigInteger)
 768 |     curator_share = db.Column(db.BigInteger)
 769 |     platform_share = db.Column(db.BigInteger)
 770 |     payment_hash = db.Column(db.String(128))
 771 |     bolt11_invoice = db.Column(db.Text)
 772 |     preimage = db.Column(db.String(128))
 773 |     status = db.Column(db.String(20), default='pending')
 774 |     source = db.Column(db.String(30))
 775 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 776 |     settled_at = db.Column(db.DateTime)
 777 |     post = db.relationship('CuratedPost', backref=db.backref('zaps', lazy='dynamic'))
 778 | 
 779 | class TrustEdge(db.Model):
 780 |     __tablename__ = 'trust_edge'
 781 |     id = db.Column(db.Integer, primary_key=True)
 782 |     truster_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 783 |     trusted_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 784 |     trust_weight = db.Column(db.Float, default=1.0)
 785 |     total_sats_via = db.Column(db.BigInteger, default=0)
 786 |     successful_curations = db.Column(db.Integer, default=0)
 787 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 788 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 789 |     __table_args__ = (db.UniqueConstraint('truster_id', 'trusted_id', name='unique_trust_edge'),)
 790 | 
 791 | class BoostStake(db.Model):
 792 |     __tablename__ = 'boost_stake'
 793 |     id = db.Column(db.Integer, primary_key=True)
 794 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 795 |     staker_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 796 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 797 |     boost_multiplier = db.Column(db.Float, default=1.0)
 798 |     expires_at = db.Column(db.DateTime)
 799 |     refunded = db.Column(db.Boolean, default=False)
 800 |     refund_amount = db.Column(db.BigInteger, default=0)
 801 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 802 |     post = db.relationship('CuratedPost', backref=db.backref('boosts', lazy='dynamic'))
 803 | 
 804 | class ExtensionSession(db.Model):
 805 |     __tablename__ = 'extension_session'
 806 |     id = db.Column(db.Integer, primary_key=True)
 807 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 808 |     session_token = db.Column(db.String(128), unique=True, nullable=False)
 809 |     browser_fingerprint = db.Column(db.String(128))
 810 |     user_agent = db.Column(db.String(500))
 811 |     is_active = db.Column(db.Boolean, default=True)
 812 |     last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
 813 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 814 |     expires_at = db.Column(db.DateTime)
 815 |     creator = db.relationship('ValueCreator', backref=db.backref('sessions', lazy='dynamic'))
 816 | 
 817 | class RollingActivity(db.Model):
 818 |     __tablename__ = 'rolling_activity'
 819 |     id = db.Column(db.Integer, primary_key=True)
 820 |     page_path = db.Column(db.String(500), nullable=False, index=True)
 821 |     page_name = db.Column(db.String(200))
 822 |     session_hash = db.Column(db.String(64), nullable=False)
 823 |     last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 824 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 825 |     
 826 |     @classmethod
 827 |     def record_activity(cls, page_path, page_name, session_hash):
 828 |         existing = cls.query.filter_by(page_path=page_path, session_hash=session_hash).first()
 829 |         if existing:
 830 |             existing.last_seen = datetime.utcnow()
 831 |         else:
 832 |             activity = cls(page_path=page_path, page_name=page_name, session_hash=session_hash, last_seen=datetime.utcnow())
 833 |             db.session.add(activity)
 834 |         try:
 835 |             db.session.commit()
 836 |         except Exception:
 837 |             db.session.rollback()
 838 | 
 839 |     @classmethod
 840 |     def get_operative_density(cls, window_minutes=30, limit=5):
 841 |         from sqlalchemy import func
 842 |         cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
 843 |         results = db.session.query(cls.page_path, cls.page_name, func.count(func.distinct(cls.session_hash)).label('count')).filter(cls.last_seen >= cutoff).group_by(cls.page_path, cls.page_name).order_by(func.count(func.distinct(cls.session_hash)).desc()).limit(limit).all()
 844 |         return results
 845 | 
 846 | class RealTimeProduct(db.Model):
 847 |     __tablename__ = 'realtime_product'
 848 |     id = db.Column(db.Integer, primary_key=True)
 849 |     statement_text = db.Column(db.String(100), nullable=False)
 850 |     design_url = db.Column(db.String(500))
 851 |     design_style = db.Column(db.String(50), default='center_chest')
 852 |     text_color = db.Column(db.String(20), default='#FFFFFF')
 853 |     trigger_state = db.Column(db.String(50))
 854 |     trigger_keywords = db.Column(db.Text)
 855 |     sentiment_score = db.Column(db.Float)
 856 |     status = db.Column(db.String(20), default='draft')
 857 |     approved_at = db.Column(db.DateTime)
 858 |     approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
 859 |     printful_product_id = db.Column(db.String(100))
 860 |     printful_sync_status = db.Column(db.String(50), default='pending')
 861 |     heat_multiplier = db.Column(db.Float, default=2.0)
 862 |     heat_expires_at = db.Column(db.DateTime)
 863 |     sarah_description = db.Column(db.Text)
 864 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 865 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 866 |     
 867 |     def is_hot(self):
 868 |         return self.heat_expires_at and datetime.utcnow() < self.heat_expires_at
 869 | 
 870 | class IntelligencePost(db.Model):
 871 |     id = db.Column(db.Integer, primary_key=True)
 872 |     persona = db.Column(db.String(20))
 873 |     partner_name = db.Column(db.String(100))
 874 |     partner_handle = db.Column(db.String(100))
 875 |     primary_tweet = db.Column(db.Text, nullable=False)
 876 |     thread_content = db.Column(db.Text)
 877 |     key_insight = db.Column(db.Text)
 878 |     source_video_id = db.Column(db.String(50))
 879 |     source_video_title = db.Column(db.String(500))
 880 |     x_tweet_id = db.Column(db.String(100))
 881 |     nostr_event_id = db.Column(db.String(100))
 882 |     engagement_likes = db.Column(db.Integer, default=0)
 883 |     engagement_retweets = db.Column(db.Integer, default=0)
 884 |     engagement_replies = db.Column(db.Integer, default=0)
 885 |     published_at = db.Column(db.DateTime, default=datetime.utcnow)
 886 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 887 | 
 888 | class SentimentReport(db.Model):
 889 |     id = db.Column(db.Integer, primary_key=True)
 890 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 891 |     report_date = db.Column(db.Date, nullable=False, unique=True)
 892 |     overall_sentiment = db.Column(db.String(20))
 893 |     sentiment_score = db.Column(db.Float)
 894 |     x_posts_analyzed = db.Column(db.Integer, default=0)
 895 |     nostr_notes_analyzed = db.Column(db.Integer, default=0)
 896 |     top_themes = db.Column(db.Text)
 897 |     key_narratives = db.Column(db.Text)
 898 |     cited_sources = db.Column(db.Text)
 899 |     raw_analysis = db.Column(db.Text)
 900 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 901 |     article = db.relationship('Article', backref='sentiment_report', lazy=True)
 902 | 
 903 | class SarahBrief(db.Model):
 904 |     __tablename__ = 'sarah_brief'
 905 |     id = db.Column(db.Integer, primary_key=True)
 906 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 907 |     brief_date = db.Column(db.Date, nullable=False, unique=True)
 908 |     macro_state = db.Column(db.Text)
 909 |     network_calibration = db.Column(db.Text)
 910 |     signal_1_title = db.Column(db.String(500))
 911 |     signal_1_source = db.Column(db.String(500))
 912 |     signal_1_url = db.Column(db.String(500))
 913 |     signal_1_impact = db.Column(db.Float, default=0.0)
 914 |     signal_2_title = db.Column(db.String(500))
 915 |     signal_2_source = db.Column(db.String(500))
 916 |     signal_2_url = db.Column(db.String(500))
 917 |     signal_2_impact = db.Column(db.Float, default=0.0)
 918 |     signal_3_title = db.Column(db.String(500))
 919 |     signal_3_source = db.Column(db.String(500))
 920 |     signal_3_url = db.Column(db.String(500))
 921 |     signal_3_impact = db.Column(db.Float, default=0.0)
 922 |     mempool_state = db.Column(db.Text)
 923 |     hashrate_state = db.Column(db.Text)
 924 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 925 |     article = db.relationship('Article', backref='sarah_brief', lazy=True)
 926 | 
 927 | class SentimentBuffer(db.Model):
 928 |     id = db.Column(db.Integer, primary_key=True)
 929 |     timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 930 |     sentiment_score = db.Column(db.Float, nullable=False)
 931 |     post_count = db.Column(db.Integer, default=0)
 932 |     dominant_theme = db.Column(db.String(200))
 933 |     source_breakdown = db.Column(db.Text)
 934 | 
 935 | class EmergencyFlash(db.Model):
 936 |     id = db.Column(db.Integer, primary_key=True)
 937 |     triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 938 |     previous_score = db.Column(db.Float)
 939 |     current_score = db.Column(db.Float)
 940 |     drift_magnitude = db.Column(db.Float)
 941 |     direction = db.Column(db.String(20))
 942 |     trigger_reason = db.Column(db.Text)
 943 |     top_signal_url = db.Column(db.String(500))
 944 |     top_signal_author = db.Column(db.String(200))
 945 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 946 |     acknowledged = db.Column(db.Boolean, default=False)
 947 |     acknowledged_at = db.Column(db.DateTime)
 948 |     article = db.relationship('Article', backref='emergency_flash', lazy=True)
 949 | 
 950 | class CollectedSignal(db.Model):
 951 |     __tablename__ = 'collected_signal'
 952 |     id = db.Column(db.Integer, primary_key=True)
 953 |     platform = db.Column(db.String(20), nullable=False)
 954 |     post_id = db.Column(db.String(100), nullable=False, unique=True)
 955 |     author_name = db.Column(db.String(200), nullable=False)
 956 |     author_handle = db.Column(db.String(100), nullable=False)
 957 |     author_tier = db.Column(db.String(50), default='general')
 958 |     content = db.Column(db.Text, nullable=False)
 959 |     url = db.Column(db.String(500), nullable=False)
 960 |     engagement_likes = db.Column(db.Integer, default=0)
 961 |     engagement_reposts = db.Column(db.Integer, default=0)
 962 |     engagement_replies = db.Column(db.Integer, default=0)
 963 |     engagement_score = db.Column(db.Float, default=0.0)
 964 |     sentiment = db.Column(db.String(20))
 965 |     sentiment_score = db.Column(db.Float)
 966 |     is_bitcoin_related = db.Column(db.Boolean, default=True)
 967 |     posted_at = db.Column(db.DateTime)
 968 |     collected_at = db.Column(db.DateTime, default=datetime.utcnow)
 969 |     is_verified = db.Column(db.Boolean, default=True)
 970 |     is_legendary = db.Column(db.Boolean, default=False)
 971 |     __table_args__ = (
 972 |         db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
 973 |         db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
 974 |     )
```

### File: core/templates/admin_affiliates.html (665 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Affiliate Analytics — Admin | Protocol Pulse{% endblock %}
   4 | 
   5 | {% block extra_css %}
   6 | <style>
   7 | /* ─── AFFILIATE ADMIN DASHBOARD ─── */
   8 | .aff-admin {
   9 |     background: #06070b;
  10 |     min-height: 100vh;
  11 |     padding: 2rem 0 4rem;
  12 |     color: #eef2ff;
  13 |     font-family: ui-sans-serif, system-ui, sans-serif;
  14 | }
  15 | .aff-page-header {
  16 |     border-bottom: 1px solid rgba(255,255,255,0.06);
  17 |     padding-bottom: 1.5rem;
  18 |     margin-bottom: 2rem;
  19 |     display: flex;
  20 |     align-items: center;
  21 |     justify-content: space-between;
  22 |     flex-wrap: wrap;
  23 |     gap: 1rem;
  24 | }
  25 | .aff-page-kicker {
  26 |     font-family: 'JetBrains Mono', monospace;
  27 |     font-size: 0.62rem;
  28 |     font-weight: 800;
  29 |     letter-spacing: 0.20em;
  30 |     text-transform: uppercase;
  31 |     color: #f8c15c;
  32 |     margin-bottom: 0.4rem;
  33 | }
  34 | .aff-page-title {
  35 |     font-size: 1.8rem;
  36 |     font-weight: 900;
  37 |     letter-spacing: -0.03em;
  38 |     color: #eef2ff;
  39 |     margin: 0;
  40 | }
  41 | .aff-refresh-btn {
  42 |     font-family: 'JetBrains Mono', monospace;
  43 |     font-size: 0.72rem;
  44 |     font-weight: 700;
  45 |     letter-spacing: 0.08em;
  46 |     background: rgba(255,255,255,0.04);
  47 |     border: 1px solid rgba(255,255,255,0.1);
  48 |     color: #95a0ba;
  49 |     padding: 0.5rem 1.2rem;
  50 |     border-radius: 8px;
  51 |     cursor: pointer;
  52 |     text-decoration: none;
  53 |     transition: color 0.2s, border-color 0.2s;
  54 | }
  55 | .aff-refresh-btn:hover { color: #eef2ff; border-color: rgba(255,255,255,0.2); }
  56 | 
  57 | /* Summary cards */
  58 | .aff-summary-grid {
  59 |     display: grid;
  60 |     grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  61 |     gap: 1rem;
  62 |     margin-bottom: 2.5rem;
  63 | }
  64 | .aff-stat-card {
  65 |     background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
  66 |     border: 1px solid rgba(255,255,255,0.08);
  67 |     border-radius: 14px;
  68 |     padding: 1.4rem 1.2rem;
  69 | }
  70 | .aff-stat-label {
  71 |     font-family: 'JetBrains Mono', monospace;
  72 |     font-size: 0.6rem;
  73 |     font-weight: 800;
  74 |     letter-spacing: 0.16em;
  75 |     text-transform: uppercase;
  76 |     color: #95a0ba;
  77 |     margin-bottom: 0.5rem;
  78 | }
  79 | .aff-stat-val {
  80 |     font-family: 'JetBrains Mono', monospace;
  81 |     font-size: 2rem;
  82 |     font-weight: 900;
  83 |     letter-spacing: -0.03em;
  84 |     color: #eef2ff;
  85 |     line-height: 1;
  86 | }
  87 | .aff-stat-sub {
  88 |     font-size: 0.75rem;
  89 |     color: #555e78;
  90 |     margin-top: 0.3rem;
  91 | }
  92 | .aff-stat-card.gold .aff-stat-val { color: #f8c15c; }
  93 | .aff-stat-card.green .aff-stat-val { color: #89ffb8; }
  94 | .aff-stat-card.red .aff-stat-val { color: #ff3b5f; }
  95 | 
  96 | /* Chart section */
  97 | .aff-chart-panel {
  98 |     background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
  99 |     border: 1px solid rgba(255,255,255,0.07);
 100 |     border-radius: 18px;
 101 |     padding: 1.8rem;
 102 |     margin-bottom: 2rem;
 103 | }
 104 | .aff-panel-header {
 105 |     display: flex;
 106 |     align-items: center;
 107 |     justify-content: space-between;
 108 |     margin-bottom: 1.4rem;
 109 |     flex-wrap: wrap;
 110 |     gap: 0.5rem;
 111 | }
 112 | .aff-panel-title {
 113 |     font-family: 'JetBrains Mono', monospace;
 114 |     font-size: 0.65rem;
 115 |     font-weight: 800;
 116 |     letter-spacing: 0.16em;
 117 |     text-transform: uppercase;
 118 |     color: #f8c15c;
 119 | }
 120 | .aff-legend {
 121 |     display: flex;
 122 |     gap: 1rem;
 123 |     font-family: 'JetBrains Mono', monospace;
 124 |     font-size: 0.62rem;
 125 |     font-weight: 700;
 126 |     letter-spacing: 0.08em;
 127 |     color: #95a0ba;
 128 | }
 129 | .aff-legend-dot {
 130 |     width: 8px; height: 8px;
 131 |     border-radius: 50%;
 132 |     display: inline-block;
 133 |     margin-right: 4px;
 134 | }
 135 | 
 136 | /* Chart bars */
 137 | .aff-bar-chart {
 138 |     display: flex;
 139 |     align-items: flex-end;
 140 |     gap: 4px;
 141 |     height: 140px;
 142 |     padding-bottom: 0;
 143 | }
 144 | .aff-bar-group {
 145 |     display: flex;
 146 |     flex-direction: column;
 147 |     align-items: center;
 148 |     gap: 2px;
 149 |     flex: 1;
 150 |     min-width: 0;
 151 | }
 152 | .aff-bar-pair {
 153 |     display: flex;
 154 |     align-items: flex-end;
 155 |     gap: 2px;
 156 |     height: 120px;
 157 |     width: 100%;
 158 | }
 159 | .aff-bar {
 160 |     flex: 1;
 161 |     border-radius: 3px 3px 0 0;
 162 |     min-height: 2px;
 163 |     transition: opacity 0.15s;
 164 | }
 165 | .aff-bar:hover { opacity: 0.7; }
 166 | .aff-bar.meanwhile { background: #f8c15c; }
 167 | .aff-bar.rns_id { background: #5de4ff; }
 168 | .aff-bar-label {
 169 |     font-family: 'JetBrains Mono', monospace;
 170 |     font-size: 0.5rem;
 171 |     color: #555e78;
 172 |     text-align: center;
 173 |     margin-top: 4px;
 174 |     white-space: nowrap;
 175 |     overflow: hidden;
 176 | }
 177 | 
 178 | /* Table */
 179 | .aff-table-panel {
 180 |     background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
 181 |     border: 1px solid rgba(255,255,255,0.07);
 182 |     border-radius: 18px;
 183 |     padding: 1.8rem;
 184 |     margin-bottom: 2rem;
 185 | }
 186 | .aff-table {
 187 |     width: 100%;
 188 |     border-collapse: collapse;
 189 |     font-size: 0.85rem;
 190 | }
 191 | .aff-table th {
 192 |     font-family: 'JetBrains Mono', monospace;
 193 |     font-size: 0.58rem;
 194 |     font-weight: 800;
 195 |     letter-spacing: 0.14em;
 196 |     text-transform: uppercase;
 197 |     color: #555e78;
 198 |     padding: 0.7rem 0.8rem;
 199 |     text-align: left;
 200 |     border-bottom: 1px solid rgba(255,255,255,0.06);
 201 | }
 202 | .aff-table td {
 203 |     padding: 0.7rem 0.8rem;
 204 |     color: #c8d0e8;
 205 |     border-bottom: 1px solid rgba(255,255,255,0.04);
 206 | }
 207 | .aff-table tr:last-child td { border-bottom: none; }
 208 | .aff-table tr:hover td { background: rgba(255,255,255,0.02); }
 209 | .aff-partner-badge {
 210 |     display: inline-block;
 211 |     font-family: 'JetBrains Mono', monospace;
 212 |     font-size: 0.58rem;
 213 |     font-weight: 800;
 214 |     letter-spacing: 0.08em;
 215 |     text-transform: uppercase;
 216 |     padding: 0.2rem 0.6rem;
 217 |     border-radius: 999px;
 218 | }
 219 | .aff-partner-badge.meanwhile { background: rgba(248,193,92,0.12); color: #f8c15c; border: 1px solid rgba(248,193,92,0.2); }
 220 | .aff-partner-badge.rns_id { background: rgba(93,228,255,0.08); color: #5de4ff; border: 1px solid rgba(93,228,255,0.15); }
 221 | 
 222 | /* A/B section */
 223 | .aff-ab-grid {
 224 |     display: grid;
 225 |     grid-template-columns: 1fr 1fr;
 226 |     gap: 1.5rem;
 227 |     margin-bottom: 2rem;
 228 | }
 229 | @media (max-width: 768px) { .aff-ab-grid { grid-template-columns: 1fr; } }
 230 | 
 231 | .aff-ab-card {
 232 |     background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
 233 |     border: 1px solid rgba(255,255,255,0.07);
 234 |     border-radius: 18px;
 235 |     padding: 1.8rem;
 236 | }
 237 | .aff-ab-partner-name {
 238 |     font-size: 1rem;
 239 |     font-weight: 700;
 240 |     color: #eef2ff;
 241 |     margin-bottom: 1.2rem;
 242 |     display: flex;
 243 |     align-items: center;
 244 |     gap: 0.6rem;
 245 | }
 246 | .aff-ab-row {
 247 |     display: flex;
 248 |     align-items: center;
 249 |     gap: 1rem;
 250 |     margin-bottom: 1rem;
 251 | }
 252 | .aff-ab-variant {
 253 |     font-family: 'JetBrains Mono', monospace;
 254 |     font-size: 0.72rem;
 255 |     font-weight: 800;
 256 |     width: 24px;
 257 |     height: 24px;
 258 |     border-radius: 6px;
 259 |     display: flex; align-items: center; justify-content: center;
 260 |     background: rgba(255,255,255,0.06);
 261 |     color: #eef2ff;
 262 |     flex-shrink: 0;
 263 | }
 264 | .aff-ab-bar-wrap {
 265 |     flex: 1;
 266 |     height: 8px;
 267 |     background: rgba(255,255,255,0.06);
 268 |     border-radius: 4px;
 269 |     overflow: hidden;
 270 | }
 271 | .aff-ab-bar-fill {
 272 |     height: 100%;
 273 |     border-radius: 4px;
 274 |     background: #f8c15c;
 275 |     transition: width 0.6s ease;
 276 | }
 277 | .aff-ab-bar-fill.rns { background: #5de4ff; }
 278 | .aff-ab-stats {
 279 |     font-family: 'JetBrains Mono', monospace;
 280 |     font-size: 0.65rem;
 281 |     color: #95a0ba;
 282 |     flex-shrink: 0;
 283 |     text-align: right;
 284 |     min-width: 90px;
 285 | }
 286 | .aff-ab-stats .ctr { font-size: 0.8rem; color: #eef2ff; font-weight: 700; }
 287 | .aff-significance {
 288 |     margin-top: 1rem;
 289 |     padding: 0.8rem 1rem;
 290 |     border-radius: 10px;
 291 |     font-size: 0.8rem;
 292 |     font-family: 'JetBrains Mono', monospace;
 293 | }
 294 | .aff-significance.sig {
 295 |     background: rgba(137,255,184,0.07);
 296 |     border: 1px solid rgba(137,255,184,0.20);
 297 |     color: #89ffb8;
 298 | }
 299 | .aff-significance.insig {
 300 |     background: rgba(255,255,255,0.03);
 301 |     border: 1px solid rgba(255,255,255,0.07);
 302 |     color: #95a0ba;
 303 | }
 304 | .aff-declare-btn {
 305 |     display: inline-block;
 306 |     margin-top: 0.8rem;
 307 |     font-family: 'JetBrains Mono', monospace;
 308 |     font-size: 0.65rem;
 309 |     font-weight: 800;
 310 |     letter-spacing: 0.08em;
 311 |     text-transform: uppercase;
 312 |     padding: 0.4rem 1rem;
 313 |     border-radius: 8px;
 314 |     background: rgba(255,59,95,0.12);
 315 |     border: 1px solid rgba(255,59,95,0.25);
 316 |     color: #ff3b5f;
 317 |     cursor: pointer;
 318 |     transition: background 0.2s;
 319 | }
 320 | .aff-declare-btn:hover { background: rgba(255,59,95,0.20); }
 321 | .aff-winner-locked {
 322 |     display: inline-flex;
 323 |     align-items: center;
 324 |     gap: 0.4rem;
 325 |     font-family: 'JetBrains Mono', monospace;
 326 |     font-size: 0.62rem;
 327 |     font-weight: 800;
 328 |     letter-spacing: 0.10em;
 329 |     text-transform: uppercase;
 330 |     color: #89ffb8;
 331 |     margin-top: 0.8rem;
 332 | }
 333 | 
 334 | /* Error notice */
 335 | .aff-error {
 336 |     background: rgba(255,59,95,0.08);
 337 |     border: 1px solid rgba(255,59,95,0.2);
 338 |     border-radius: 12px;
 339 |     padding: 1rem 1.5rem;
 340 |     color: #ff8ba0;
 341 |     font-size: 0.85rem;
 342 |     margin-bottom: 1.5rem;
 343 | }
 344 | 
 345 | /* Responsive */
 346 | @media (max-width: 768px) {
 347 |     .aff-bar-chart { height: 100px; }
 348 |     .aff-summary-grid { grid-template-columns: repeat(2, 1fr); }
 349 | }
 350 | </style>
 351 | {% endblock %}
 352 | 
 353 | {% block content %}
 354 | <div class="aff-admin">
 355 | <div class="container">
 356 | 
 357 |   <!-- PAGE HEADER -->
 358 |   <div class="aff-page-header">
 359 |     <div>
 360 |       <div class="aff-page-kicker">Admin &nbsp;•&nbsp; P3 Revenue</div>
 361 |       <h1 class="aff-page-title">Affiliate Analytics</h1>
 362 |     </div>
 363 |     <a href="/admin/affiliates" class="aff-refresh-btn" aria-label="Refresh data">↺ Refresh</a>
 364 |   </div>
 365 | 
 366 |   {% if error %}
 367 |   <div class="aff-error">
 368 |     <strong>Error:</strong> {{ error }}
 369 |     <br><small>Check logs. Tables will be created on next /go/meanwhile or /go/rns request.</small>
 370 |   </div>
 371 |   {% endif %}
 372 | 
 373 |   <!-- SUMMARY CARDS -->
 374 |   {% set mw = totals_map.get('meanwhile', {'total':0,'unique_users':0}) %}
 375 |   {% set rns = totals_map.get('rns_id', {'total':0,'unique_users':0}) %}
 376 |   {% set total_all = mw.total + rns.total %}
 377 |   {% set est_mw = (mw.total * 0.02 * 150) | round(2) %}
 378 |   {% set est_rns = (rns.total * 0.02 * 300) | round(2) %}
 379 |   {% set est_total = (est_mw + est_rns) | round(2) %}
 380 | 
 381 |   <div class="aff-summary-grid">
 382 |     <div class="aff-stat-card">
 383 |       <div class="aff-stat-label">Total Clicks (30d)</div>
 384 |       <div class="aff-stat-val">{{ total_all }}</div>
 385 |       <div class="aff-stat-sub">Both partners combined</div>
 386 |     </div>
 387 |     <div class="aff-stat-card">
 388 |       <div class="aff-stat-label">Meanwhile Clicks</div>
 389 |       <div class="aff-stat-val">{{ mw.total }}</div>
 390 |       <div class="aff-stat-sub">{{ mw.unique_users }} unique users</div>
 391 |     </div>
 392 |     <div class="aff-stat-card">
 393 |       <div class="aff-stat-label">RNS.ID Clicks</div>
 394 |       <div class="aff-stat-val">{{ rns.total }}</div>
 395 |       <div class="aff-stat-sub">{{ rns.unique_users }} unique users</div>
 396 |     </div>
 397 |     <div class="aff-stat-card gold">
 398 |       <div class="aff-stat-label">Est. Earnings</div>
 399 |       <div class="aff-stat-val">${{ est_total }}</div>
 400 |       <div class="aff-stat-sub">2% conv × commission</div>
 401 |     </div>
 402 |     <div class="aff-stat-card green">
 403 |       <div class="aff-stat-label">Est. Meanwhile</div>
 404 |       <div class="aff-stat-val">${{ est_mw }}</div>
 405 |       <div class="aff-stat-sub">$150 avg commission</div>
 406 |     </div>
 407 |     <div class="aff-stat-card" style="border-color:rgba(93,228,255,0.12);">
 408 |       <div class="aff-stat-label">Est. RNS.ID</div>
 409 |       <div class="aff-stat-val" style="color:#5de4ff;">${{ est_rns }}</div>
 410 |       <div class="aff-stat-sub">$300 per referral</div>
 411 |     </div>
 412 |   </div>
 413 | 
 414 |   <!-- CLICKS CHART -->
 415 |   <div class="aff-chart-panel">
 416 |     <div class="aff-panel-header">
 417 |       <div class="aff-panel-title">Clicks Per Day — Last 30 Days</div>
 418 |       <div class="aff-legend">
 419 |         <span><span class="aff-legend-dot" style="background:#f8c15c;"></span>Meanwhile</span>
 420 |         <span><span class="aff-legend-dot" style="background:#5de4ff;"></span>RNS.ID</span>
 421 |       </div>
 422 |     </div>
 423 |     <div class="aff-bar-chart" id="affBarChart" role="img" aria-label="Daily affiliate clicks chart">
 424 |       <!-- Rendered by JS below -->
 425 |       <noscript><p style="color:#95a0ba;font-size:0.8rem;">Enable JavaScript to view chart.</p></noscript>
 426 |     </div>
 427 |   </div>
 428 | 
 429 |   <!-- A/B TEST RESULTS -->
 430 |   <div class="aff-page-kicker" style="margin-bottom:1rem;">A/B Test Results — Thompson Sampling MAB</div>
 431 |   <div class="aff-ab-grid">
 432 | 
 433 |     {% for partner_key, stats in ab_stats.items() %}
 434 |     {% set partner_label = 'Meanwhile' if partner_key == 'meanwhile' else 'RNS.ID' %}
 435 |     {% set accent = 'meanwhile' if partner_key == 'meanwhile' else 'rns_id' %}
 436 |     <div class="aff-ab-card">
 437 |       <div class="aff-ab-partner-name">
 438 |         <span class="aff-partner-badge {{ accent }}">{{ accent }}</span>
 439 |         {{ partner_label }} — A/B Test
 440 |       </div>
 441 | 
 442 |       {% if stats.get('error') %}
 443 |       <p style="color:#555e78;font-size:0.82rem;">No data yet. Run traffic to see results.</p>
 444 |       {% else %}
 445 |       {% set va = stats.get('variant_a', {}) %}
 446 |       {% set vb = stats.get('variant_b', {}) %}
 447 |       {% set max_ctr = [va.get('ctr',0), vb.get('ctr',0), 0.01] | max %}
 448 | 
 449 |       <div class="aff-ab-row">
 450 |         <span class="aff-ab-variant">A</span>
 451 |         <div class="aff-ab-bar-wrap">
 452 |           <div class="aff-ab-bar-fill {% if accent == 'rns_id' %}rns{% endif %}"
 453 |                style="width:{{ ((va.get('ctr',0) / max_ctr * 100) | round) | int }}%"></div>
 454 |         </div>
 455 |         <div class="aff-ab-stats">
 456 |           <span class="ctr">{{ va.get('ctr', 0) }}%</span><br>
 457 |           {{ va.get('clicks',0) }}/{{ va.get('impressions',0) }}
 458 |         </div>
 459 |       </div>
 460 | 
 461 |       <div class="aff-ab-row">
 462 |         <span class="aff-ab-variant">B</span>
 463 |         <div class="aff-ab-bar-wrap">
 464 |           <div class="aff-ab-bar-fill {% if accent == 'rns_id' %}rns{% endif %}"
 465 |                style="width:{{ ((vb.get('ctr',0) / max_ctr * 100) | round) | int }}%"></div>
 466 |         </div>
 467 |         <div class="aff-ab-stats">
 468 |           <span class="ctr">{{ vb.get('ctr', 0) }}%</span><br>
 469 |           {{ vb.get('clicks',0) }}/{{ vb.get('impressions',0) }}
 470 |         </div>
 471 |       </div>
 472 | 
 473 |       {% if stats.get('needs_more_data') %}
 474 |       <div class="aff-significance insig">
 475 |         Need more data — {{ [va.get('impressions',0), vb.get('impressions',0)] | min }}/100 impressions per variant
 476 |       </div>
 477 |       {% elif stats.get('significant') %}
 478 |       <div class="aff-significance sig">
 479 |         ✓ Variant {{ stats.winning_variant }} wins — {{ stats.confidence_pct }}% confidence (z={{ stats.z_score }})
 480 |       </div>
 481 |       <button class="aff-declare-btn"
 482 |               onclick="declareWinner('{{ partner_key }}','{{ stats.winning_variant }}')"
 483 |               aria-label="Lock in Variant {{ stats.winning_variant }} as winner for {{ partner_label }}">
 484 |         Lock In Variant {{ stats.winning_variant }} →
 485 |       </button>
 486 |       {% else %}
 487 |       <div class="aff-significance insig">
 488 |         No significant difference yet (z={{ stats.get('z_score','—') }}, p={{ stats.get('p_value','—') }})
 489 |       </div>
 490 |       {% endif %}
 491 |       {% endif %}
 492 |     </div>
 493 |     {% endfor %}
 494 | 
 495 |   </div>
 496 | 
 497 |   <!-- TOP REFERRER PAGES -->
 498 |   <div class="aff-table-panel">
 499 |     <div class="aff-panel-header">
 500 |       <div class="aff-panel-title">Top Referrer Pages — 30 Days</div>
 501 |       <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:#555e78;">
 502 |         k≥{{ k_anon }} user threshold (privacy)
 503 |       </span>
 504 |     </div>
 505 |     {% if top_refs %}
 506 |     <div style="overflow-x:auto;">
 507 |       <table class="aff-table" aria-label="Top referrer pages by affiliate clicks">
 508 |         <thead>
 509 |           <tr>
 510 |             <th>Partner</th>
 511 |             <th>Page</th>
 512 |             <th>Clicks</th>
 513 |             <th>Unique Users</th>
 514 |             <th>Est. Value</th>
 515 |           </tr>
 516 |         </thead>
 517 |         <tbody>
 518 |           {% for ref in top_refs %}
 519 |           {% set comm = 150 if ref[0] == 'meanwhile' else 300 %}
 520 |           <tr>
 521 |             <td><span class="aff-partner-badge {{ ref[0] }}">{{ ref[0] }}</span></td>
 522 |             <td style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#95a0ba;">
 523 |               {{ ref[1][:60] }}{% if ref[1]|length > 60 %}…{% endif %}
 524 |             </td>
 525 |             <td style="font-family:'JetBrains Mono',monospace;font-weight:700;">{{ ref[2] }}</td>
 526 |             <td style="font-family:'JetBrains Mono',monospace;color:#95a0ba;">{{ ref[3] }}</td>
 527 |             <td style="font-family:'JetBrains Mono',monospace;color:#f8c15c;">
 528 |               ${{ (ref[2] * 0.02 * comm) | round(2) }}
 529 |             </td>
 530 |           </tr>
 531 |           {% endfor %}
 532 |         </tbody>
 533 |       </table>
 534 |     </div>
 535 |     {% else %}
 536 |     <p style="color:#555e78;font-size:0.85rem;padding:1rem 0;">
 537 |       No data yet — or all pages below k={{ k_anon }} user threshold.
 538 |     </p>
 539 |     {% endif %}
 540 |   </div>
 541 | 
 542 |   <!-- QUICK LINKS -->
 543 |   <div style="display:flex;gap:1rem;flex-wrap:wrap;">
 544 |     <a href="/bitcoin-life-insurance" target="_blank" class="aff-refresh-btn">↗ Meanwhile Landing Page</a>
 545 |     <a href="/digital-residency" target="_blank" class="aff-refresh-btn">↗ RNS.ID Landing Page</a>
 546 |     <a href="/go/meanwhile?ref=admin-test&v=A" target="_blank" class="aff-refresh-btn">Test /go/meanwhile</a>
 547 |     <a href="/go/rns?ref=admin-test&v=A" target="_blank" class="aff-refresh-btn">Test /go/rns</a>
 548 |     <a href="/api/affiliates/metrics" target="_blank" class="aff-refresh-btn">API Metrics JSON</a>
 549 |   </div>
 550 | 
 551 | </div>
 552 | </div>
 553 | 
 554 | <!-- Chart data injected as JSON -->
 555 | <script id="aff-chart-data" type="application/json">
 556 | {
 557 |   "clicks_by_day": {{ clicks_by_day | tojson }},
 558 |   "meanwhile_color": "#f8c15c",
 559 |   "rns_color": "#5de4ff"
 560 | }
 561 | </script>
 562 | {% endblock %}
 563 | 
 564 | {% block extra_js %}
 565 | <script>
 566 | (function() {
 567 |     // ── Chart rendering ──
 568 |     var raw = {};
 569 |     try { raw = JSON.parse(document.getElementById('aff-chart-data').textContent); } catch(e) {}
 570 |     var mwData = raw.clicks_by_day && raw.clicks_by_day.meanwhile || {};
 571 |     var rnsData = raw.clicks_by_day && raw.clicks_by_day.rns_id || {};
 572 | 
 573 |     // Build 30-day date list
 574 |     var dates = [];
 575 |     var now = new Date();
 576 |     for (var i = 29; i >= 0; i--) {
 577 |         var d = new Date(now);
 578 |         d.setDate(d.getDate() - i);
 579 |         var iso = d.toISOString().slice(0, 10);
 580 |         dates.push(iso);
 581 |     }
 582 | 
 583 |     // Find max for scaling
 584 |     var maxVal = 1;
 585 |     dates.forEach(function(d) {
 586 |         var v = (mwData[d] || 0) + (rnsData[d] || 0);
 587 |         if (v > maxVal) maxVal = v;
 588 |     });
 589 | 
 590 |     var chart = document.getElementById('affBarChart');
 591 |     if (!chart) return;
 592 |     chart.innerHTML = '';
 593 | 
 594 |     dates.forEach(function(d) {
 595 |         var mwV = mwData[d] || 0;
 596 |         var rnsV = rnsData[d] || 0;
 597 |         var maxH = 110; // px
 598 | 
 599 |         var group = document.createElement('div');
 600 |         group.className = 'aff-bar-group';
 601 |         group.title = d + ': Meanwhile=' + mwV + ', RNS.ID=' + rnsV;
 602 | 
 603 |         var pair = document.createElement('div');
 604 |         pair.className = 'aff-bar-pair';
 605 | 
 606 |         var b1 = document.createElement('div');
 607 |         b1.className = 'aff-bar meanwhile';
 608 |         b1.style.height = Math.max(2, Math.round(mwV / maxVal * maxH)) + 'px';
 609 | 
 610 |         var b2 = document.createElement('div');
 611 |         b2.className = 'aff-bar rns_id';
 612 |         b2.style.height = Math.max(2, Math.round(rnsV / maxVal * maxH)) + 'px';
 613 | 
 614 |         pair.appendChild(b1);
 615 |         pair.appendChild(b2);
 616 | 
 617 |         var label = document.createElement('div');
 618 |         label.className = 'aff-bar-label';
 619 |         // Show day/month only every 5 days
 620 |         var idx = dates.indexOf(d);
 621 |         if (idx % 5 === 0 || idx === 29) {
 622 |             label.textContent = d.slice(5); // MM-DD
 623 |         }
 624 | 
 625 |         group.appendChild(pair);
 626 |         group.appendChild(label);
 627 |         chart.appendChild(group);
 628 |     });
 629 | })();
 630 | 
 631 | // ── Declare winner ──
 632 | function declareWinner(partner, variant) {
 633 |     if (!confirm('Lock Variant ' + variant + ' as permanent winner for ' + partner + '?\nThis will freeze the MAB allocation. Cannot be undone easily.')) return;
 634 | 
 635 |     var btn = event.currentTarget || document.querySelector('[onclick*="' + partner + '"]');
 636 |     if (btn) btn.disabled = true;
 637 | 
 638 |     fetch('/api/affiliates/declare-winner', {
 639 |         method: 'POST',
 640 |         headers: {'Content-Type': 'application/json'},
 641 |         body: JSON.stringify({partner: partner, variant: variant})
 642 |     })
 643 |     .then(function(r) { return r.json(); })
 644 |     .then(function(data) {
 645 |         if (data.ok) {
 646 |             var card = btn ? btn.closest('.aff-ab-card') : null;
 647 |             if (card) {
 648 |                 var locked = document.createElement('div');
 649 |                 locked.className = 'aff-winner-locked';
 650 |                 locked.textContent = '✓ Variant ' + variant + ' Locked as Winner';
 651 |                 btn.replaceWith(locked);
 652 |             }
 653 |         } else {
 654 |             alert('Error: ' + (data.error || 'unknown'));
 655 |             if (btn) btn.disabled = false;
 656 |         }
 657 |     })
 658 |     .catch(function(e) {
 659 |         alert('Network error: ' + e.message);
 660 |         if (btn) btn.disabled = false;
 661 |     });
 662 | }
 663 | </script>
 664 | {% endblock %}
 665 | 
```

### File: core/templates/article_detail.html (662 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}{{ article.title }} - Protocol Pulse{% endblock %}
   4 | 
   5 | {% block meta_description %}{{ article.summary if article.summary else article.content[:150] }}{% endblock %}
   6 | 
   7 | {% block extra_css %}
   8 | <style>
   9 | /* ── P3 Affiliate CTA styles ── */
  10 | .affiliate-card {
  11 |     margin: 2rem 0;
  12 |     border-radius: 14px;
  13 |     overflow: hidden;
  14 | }
  15 | .aff-card-inner {
  16 |     background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
  17 |     border: 1px solid rgba(255,255,255,0.08);
  18 |     border-left: 4px solid #ff3b5f;
  19 |     border-radius: 14px;
  20 |     padding: 1.5rem 1.6rem;
  21 |     position: relative;
  22 | }
  23 | .aff-card-badge {
  24 |     font-family: 'JetBrains Mono', monospace;
  25 |     font-size: 0.58rem;
  26 |     font-weight: 800;
  27 |     letter-spacing: 0.16em;
  28 |     text-transform: uppercase;
  29 |     color: #555e78;
  30 |     margin-bottom: 0.9rem;
  31 | }
  32 | .aff-card-header {
  33 |     display: flex;
  34 |     align-items: center;
  35 |     gap: 0.8rem;
  36 |     margin-bottom: 0.8rem;
  37 | }
  38 | .aff-card-icon { font-size: 1.4rem; }
  39 | .aff-card-title {
  40 |     display: block;
  41 |     font-weight: 800;
  42 |     font-size: 1rem;
  43 |     color: #eef2ff;
  44 |     line-height: 1.2;
  45 | }
  46 | .aff-card-subtitle {
  47 |     display: block;
  48 |     font-size: 0.78rem;
  49 |     color: #95a0ba;
  50 | }
  51 | .aff-card-pitch {
  52 |     font-size: 0.9rem;
  53 |     color: #c8d0e8;
  54 |     line-height: 1.6;
  55 |     margin-bottom: 1rem;
  56 | }
  57 | .aff-card-cta {
  58 |     display: inline-flex;
  59 |     align-items: center;
  60 |     gap: 0.3rem;
  61 |     background: #ff3b5f;
  62 |     color: #fff !important;
  63 |     font-weight: 700;
  64 |     font-size: 0.85rem;
  65 |     padding: 0.5rem 1.2rem;
  66 |     border-radius: 7px;
  67 |     text-decoration: none !important;
  68 |     transition: background 0.2s, transform 0.15s;
  69 | }
  70 | .aff-card-cta:hover { background: #e0364f; transform: translateY(-1px); }
  71 | .aff-cta-green { background: #00d68f !important; color: #06070b !important; }
  72 | .aff-cta-green:hover { background: #00c07d !important; }
  73 | .affiliate-inline {
  74 |     display: block;
  75 |     font-size: 0.92rem;
  76 |     color: #95a0ba;
  77 |     border-left: 2px solid rgba(255,59,95,0.3);
  78 |     padding: 0.5rem 1rem;
  79 |     margin: 1.5rem 0;
  80 |     font-style: italic;
  81 |     line-height: 1.6;
  82 | }
  83 | .aff-link-inline {
  84 |     color: #f8c15c;
  85 |     text-decoration: none;
  86 |     border-bottom: 1px dashed rgba(248,193,92,0.4);
  87 | }
  88 | .aff-link-inline:hover { color: #ffd580; border-bottom-color: #ffd580; }
  89 | </style>
  90 | {% endblock %}
  91 | 
  92 | {% block head %}
  93 | <!-- Open Graph meta tags for social media sharing -->
  94 | <meta property="og:title" content="{{ article.title }}">
  95 | <meta property="og:description" content="{{ article.content[:200] }}...">
  96 | <meta property="og:image" content="{{ article.header_image_url or url_for('dynamic_og_image', og_type='article', id=article.id) }}">
  97 | <meta property="og:url" content="{{ request.url }}">
  98 | <meta property="og:type" content="article">
  99 | <meta property="og:site_name" content="Protocol Pulse">
 100 | 
 101 | <!-- Twitter Card meta tags -->
 102 | <meta name="twitter:card" content="summary_large_image">
 103 | <meta name="twitter:site" content="@protocolpulse">
 104 | <meta name="twitter:title" content="{{ article.title }}">
 105 | <meta name="twitter:description" content="{{ article.content[:200] }}...">
 106 | <meta name="twitter:image" content="{{ article.header_image_url or url_for('dynamic_og_image', og_type='article', id=article.id) }}">
 107 | 
 108 | <!-- SEO meta tags -->
 109 | <meta name="description" content="{{ article.seo_description or article.summary }}">
 110 | <meta name="keywords" content="{{ article.tags }}, Bitcoin, DeFi, Protocol Pulse">
 111 | <link rel="canonical" href="{{ request.url }}">
 112 | {% endblock %}
 113 | 
 114 | {% block content %}
 115 | <div class="reading-progress"></div>
 116 | 
 117 | <article class="py-5">
 118 |     <div class="container">
 119 |         <!-- Article Header -->
 120 |         <div class="row justify-content-center">
 121 |             <div class="col-lg-8">
 122 |                 <div class="mb-4">
 123 |                     <nav aria-label="breadcrumb">
 124 |                         <ol class="breadcrumb">
 125 |                             <li class="breadcrumb-item"><a href="{{ url_for('index') }}" class="text-primary">Home</a></li>
 126 |                             <li class="breadcrumb-item"><a href="{{ url_for('articles') }}" class="text-primary">News</a></li>
 127 |                             <li class="breadcrumb-item active text-muted" aria-current="page">{{ article.title[:50] }}...</li>
 128 |                         </ol>
 129 |                     </nav>
 130 |                 </div>
 131 | 
 132 |                 <header class="article-header-professional">
 133 |                     <!-- Category Badge -->
 134 |                     <div class="category-section mb-4">
 135 |                         <span class="category-badge">{{ article.category }}</span>
 136 |                     </div>
 137 | 
 138 |                     <!-- Article Title -->
 139 |                     <h1 class="article-title-professional">{{ article.title }}</h1>
 140 | 
 141 |                     <!-- Author and Date -->
 142 |                     <div class="article-meta-professional mb-4">
 143 |                         <div class="meta-item">
 144 |                             <span class="meta-label">By</span>
 145 |                             <span class="meta-value">{{ article.author }}</span>
 146 |                         </div>
 147 |                         <div class="meta-divider">•</div>
 148 |                         <div class="meta-item">
 149 |                             <span class="meta-value">{{ article.created_at.strftime('%B %d, %Y at %I:%M %p') }}</span>
 150 |                         </div>
 151 |                         <div class="meta-divider">•</div>
 152 |                         <div class="meta-item">
 153 |                             <span class="meta-value">{{ ((article.content | length) / 1000 * 3) | round | int }} min read</span>
 154 |                         </div>
 155 |                         <div class="meta-divider">•</div>
 156 |                         <div class="meta-item">
 157 |                             <span class="meta-label">Source</span>
 158 |                             {% set src_url = (article.source_url or '')|trim %}
 159 |                             {% set src_type = (article.source_type or '')|trim %}
 160 |                             {% if src_url %}
 161 |                                 <a class="meta-value" href="{{ src_url }}" target="_blank" rel="noopener" style="text-decoration: none; border-bottom: 1px dotted rgba(220,38,38,0.45);">
 162 |                                     {{ src_type if src_type else "Link" }}
 163 |                                 </a>
 164 |                             {% else %}
 165 |                                 <span class="meta-value">{{ src_type if src_type else "Protocol Pulse AI" }}</span>
 166 |                             {% endif %}
 167 |                         </div>
 168 |                     </div>
 169 | 
 170 |                     {% if article.header_image_url %}
 171 |                     <!-- Hero Image -->
 172 |                     <div class="article-image-hero mb-4">
 173 |                         <img src="{{ article.header_image_url }}" alt="{{ article.title }}" class="img-fluid w-100">
 174 |                     </div>
 175 |                     {% endif %}
 176 | 
 177 |                     <!-- Share Buttons -->
 178 |                     <div class="share-social-section">
 179 |                         <div class="share-label">Share:</div>
 180 |                         <div class="share-buttons">
 181 |                             <a href="https://twitter.com/intent/tweet?text={{ article.title | urlencode }}&url={{ request.url | urlencode }}"
 182 |                                target="_blank" class="share-btn twitter" title="Share on Twitter">
 183 |                                 <i class="fab fa-twitter"></i>
 184 |                             </a>
 185 |                             <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ request.url | urlencode }}"
 186 |                                target="_blank" class="share-btn linkedin" title="Share on LinkedIn">
 187 |                                 <i class="fab fa-linkedin"></i>
 188 |                             </a>
 189 |                             <a href="mailto:?subject={{ article.title | urlencode }}&body={{ request.url | urlencode }}"
 190 |                                class="share-btn email" title="Share via Email">
 191 |                                 <i class="fas fa-envelope"></i>
 192 |                             </a>
 193 |                             <button onclick="copyToClipboard('{{ request.url }}')" class="share-btn copy" title="Copy Link">
 194 |                                 <i class="fas fa-link"></i>
 195 |                             </button>
 196 |                         </div>
 197 |                     </div>
 198 |                 </header>
 199 | 
 200 |                 <!-- Article Content -->
 201 |                 <div class="article-content-professional">
 202 |                     {% if key_takeaways_bullets %}
 203 |                     <!-- Key Takeaways Section -->
 204 |                     <div class="key-takeaways-section mb-5">
 205 |                         <h3 class="section-title">Key Takeaways</h3>
 206 |                         <ul class="takeaways-list">
 207 |                             {% for bullet in key_takeaways_bullets %}
 208 |                             <li>{{ bullet }}</li>
 209 |                             {% endfor %}
 210 |                         </ul>
 211 |                     </div>
 212 |                     {% endif %}
 213 | 
 214 |                     <!-- Main Content -->
 215 |                     <div class="article-body">
 216 |                         {{ article.content | safe }}
 217 |                     </div>
 218 |                 </div>
 219 | 
 220 |                 <!-- P3 Affiliate CTA — Contextual, AI-classified, intent-gated -->
 221 |                 {% if affiliate_cta %}
 222 |                 <div class="aff-cta-container"
 223 |                      data-partner="{{ affiliate_cta.partner }}"
 224 |                      data-variant="{{ affiliate_cta.variant }}"
 225 |                      data-referrer="{{ request.path }}"
 226 |                      id="affCtaBlock"
 227 |                      style="opacity:0;transition:opacity 0.4s ease;margin:2.5rem 0;">
 228 |                   {{ affiliate_cta.cta_html | safe }}
 229 |                 </div>
 230 |                 {% endif %}
 231 | 
 232 |                 <!-- Article Footer -->
 233 |                 <footer class="article-footer-professional mt-5 pt-4">
 234 |                     <div class="footer-section">
 235 |                         <h4 class="footer-title">About Protocol Pulse</h4>
 236 |                         <p class="footer-text">Protocol Pulse delivers real-time intelligence for Bitcoin transactors. Technical storytelling, verified data, zero fabrication.</p>
 237 |                     </div>
 238 | 
 239 |                     <div class="footer-section">
 240 |                         <h4 class="footer-title">Stay Updated</h4>
 241 |                         <p class="footer-text mb-3">Get daily intelligence briefings delivered to your inbox.</p>
 242 |                         <form action="{{ url_for('newsletter_subscribe') }}" method="POST" class="footer-subscribe-form">
 243 |                             <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
 244 |                             <div class="input-group">
 245 |                                 <input type="email" name="email" class="form-control" placeholder="Enter your email" required>
 246 |                                 <button type="submit" class="btn btn-primary">Subscribe</button>
 247 |                             </div>
 248 |                         </form>
 249 |                     </div>
 250 |                 </footer>
 251 |             </div>
 252 |         </div>
 253 | 
 254 |         <!-- Related Articles -->
 255 |         {% if related_articles %}
 256 |         <section class="related-articles-section mt-5">
 257 |             <div class="row justify-content-center">
 258 |                 <div class="col-lg-10">
 259 |                     <h3 class="section-title mb-4">Related Intelligence</h3>
 260 |                     <div class="row g-4">
 261 |                         {% for related in related_articles %}
 262 |                         <div class="col-md-4">
 263 |                             <a href="{{ url_for('article_detail', article_id=related.id) }}" class="related-article-card">
 264 |                                 {% if related.header_image_url %}
 265 |                                 <div class="related-image">
 266 |                                     <img src="{{ related.header_image_url }}" alt="{{ related.title }}" class="img-fluid">
 267 |                                 </div>
 268 |                                 {% endif %}
 269 |                                 <div class="related-content">
 270 |                                     <div class="related-category">{{ related.category }}</div>
 271 |                                     <h4 class="related-title">{{ related.title }}</h4>
 272 |                                     <div class="related-date">{{ related.created_at.strftime('%b %d, %Y') }}</div>
 273 |                                 </div>
 274 |                             </a>
 275 |                         </div>
 276 |                         {% endfor %}
 277 |                     </div>
 278 |                 </div>
 279 |             </div>
 280 |         </section>
 281 |         {% endif %}
 282 |     </div>
 283 | </article>
 284 | 
 285 | <!-- Copy to Clipboard Toast -->
 286 | <div class="toast-container position-fixed bottom-0 end-0 p-3">
 287 |     <div id="copyToast" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
 288 |         <div class="toast-body">
 289 |             Link copied to clipboard!
 290 |         </div>
 291 |     </div>
 292 | </div>
 293 | 
 294 | <style>
 295 |     /* Reading progress bar */
 296 |     .reading-progress {
 297 |         position: fixed;
 298 |         top: 0;
 299 |         left: 0;
 300 |         width: 0%;
 301 |         height: 3px;
 302 |         background: linear-gradient(90deg, #dc2626 0%, #f7931a 100%);
 303 |         z-index: 9999;
 304 |         transition: width 0.1s ease;
 305 |     }
 306 | 
 307 |     /* Professional article header styles */
 308 |     .article-header-professional {
 309 |         margin-bottom: 3rem;
 310 |     }
 311 | 
 312 |     .category-badge {
 313 |         display: inline-block;
 314 |         background: rgba(220, 38, 38, 0.1);
 315 |         color: #dc2626;
 316 |         padding: 0.5rem 1rem;
 317 |         border-radius: 50px;
 318 |         font-size: 0.875rem;
 319 |         font-weight: 600;
 320 |         text-transform: uppercase;
 321 |         letter-spacing: 0.5px;
 322 |     }
 323 | 
 324 |     .article-title-professional {
 325 |         font-size: 2.75rem;
 326 |         font-weight: 700;
 327 |         line-height: 1.2;
 328 |         margin-bottom: 1.5rem;
 329 |         color: #fff;
 330 |         font-family: 'Crimson Pro', serif;
 331 |     }
 332 | 
 333 |     .article-meta-professional {
 334 |         display: flex;
 335 |         align-items: center;
 336 |         flex-wrap: wrap;
 337 |         gap: 1rem;
 338 |         color: rgba(255, 255, 255, 0.7);
 339 |         font-size: 0.95rem;
 340 |     }
 341 | 
 342 |     .meta-item {
 343 |         display: flex;
 344 |         align-items: center;
 345 |         gap: 0.5rem;
 346 |     }
 347 | 
 348 |     .meta-label {
 349 |         font-weight: 500;
 350 |     }
 351 | 
 352 |     .meta-value {
 353 |         font-weight: 600;
 354 |         color: rgba(255, 255, 255, 0.9);
 355 |     }
 356 | 
 357 |     .meta-divider {
 358 |         color: rgba(255, 255, 255, 0.4);
 359 |     }
 360 | 
 361 |     .article-image-hero {
 362 |         border-radius: 16px;
 363 |         overflow: hidden;
 364 |         box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
 365 |     }
 366 | 
 367 |     .article-image-hero img {
 368 |         width: 100%;
 369 |         height: auto;
 370 |         object-fit: cover;
 371 |     }
 372 | 
 373 |     /* Share buttons */
 374 |     .share-social-section {
 375 |         display: flex;
 376 |         align-items: center;
 377 |         gap: 1rem;
 378 |         padding: 1.5rem;
 379 |         background: rgba(255, 255, 255, 0.03);
 380 |         border-radius: 12px;
 381 |         border: 1px solid rgba(255, 255, 255, 0.08);
 382 |     }
 383 | 
 384 |     .share-label {
 385 |         font-weight: 600;
 386 |         color: rgba(255, 255, 255, 0.8);
 387 |     }
 388 | 
 389 |     .share-buttons {
 390 |         display: flex;
 391 |         gap: 0.75rem;
 392 |     }
 393 | 
 394 |     .share-btn {
 395 |         width: 40px;
 396 |         height: 40px;
 397 |         border-radius: 10px;
 398 |         display: flex;
 399 |         align-items: center;
 400 |         justify-content: center;
 401 |         text-decoration: none;
 402 |         border: none;
 403 |         cursor: pointer;
 404 |         transition: all 0.2s ease;
 405 |         font-size: 1.1rem;
 406 |     }
 407 | 
 408 |     .share-btn.twitter {
 409 |         background: rgba(29, 161, 242, 0.1);
 410 |         color: #1da1f2;
 411 |     }
 412 | 
 413 |     .share-btn.linkedin {
 414 |         background: rgba(0, 119, 181, 0.1);
 415 |         color: #0077b5;
 416 |     }
 417 | 
 418 |     .share-btn.email {
 419 |         background: rgba(220, 38, 38, 0.1);
 420 |         color: #dc2626;
 421 |     }
 422 | 
 423 |     .share-btn.copy {
 424 |         background: rgba(247, 147, 26, 0.1);
 425 |         color: #f7931a;
 426 |     }
 427 | 
 428 |     .share-btn:hover {
 429 |         transform: translateY(-2px);
 430 |         box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
 431 |         color: #fff;
 432 |     }
 433 | 
 434 |     /* Article content */
 435 |     .article-content-professional {
 436 |         font-size: 1.1rem;
 437 |         line-height: 1.8;
 438 |         color: rgba(255, 255, 255, 0.85);
 439 |         font-family: 'DM Sans', sans-serif;
 440 |     }
 441 | 
 442 |     .section-title {
 443 |         font-size: 1.5rem;
 444 |         font-weight: 700;
 445 |         margin-bottom: 1.5rem;
 446 |         color: #fff;
 447 |         font-family: 'Crimson Pro', serif;
 448 |     }
 449 | 
 450 |     .key-takeaways-section {
 451 |         background: rgba(220, 38, 38, 0.05);
 452 |         border: 1px solid rgba(220, 38, 38, 0.15);
 453 |         border-radius: 16px;
 454 |         padding: 2rem;
 455 |     }
 456 | 
 457 |     .takeaways-list {
 458 |         list-style: none;
 459 |         padding: 0;
 460 |         margin: 0;
 461 |     }
 462 | 
 463 |     .takeaways-list li {
 464 |         padding: 0.75rem 0;
 465 |         padding-left: 2rem;
 466 |         position: relative;
 467 |         border-bottom: 1px solid rgba(255, 255, 255, 0.05);
 468 |     }
 469 | 
 470 |     .takeaways-list li:last-child {
 471 |         border-bottom: none;
 472 |     }
 473 | 
 474 |     .takeaways-list li::before {
 475 |         content: '→';
 476 |         position: absolute;
 477 |         left: 0;
 478 |         color: #dc2626;
 479 |         font-weight: bold;
 480 |     }
 481 | 
 482 |     /* Footer */
 483 |     .article-footer-professional {
 484 |         border-top: 1px solid rgba(255, 255, 255, 0.08);
 485 |         display: grid;
 486 |         grid-template-columns: 1fr 1fr;
 487 |         gap: 3rem;
 488 |     }
 489 | 
 490 |     .footer-title {
 491 |         font-size: 1.1rem;
 492 |         font-weight: 700;
 493 |         color: #fff;
 494 |         margin-bottom: 1rem;
 495 |     }
 496 | 
 497 |     .footer-text {
 498 |         color: rgba(255, 255, 255, 0.7);
 499 |         line-height: 1.6;
 500 |     }
 501 | 
 502 |     /* Related articles */
 503 |     .related-article-card {
 504 |         display: block;
 505 |         background: rgba(255, 255, 255, 0.03);
 506 |         border: 1px solid rgba(255, 255, 255, 0.08);
 507 |         border-radius: 16px;
 508 |         overflow: hidden;
 509 |         text-decoration: none;
 510 |         transition: all 0.3s ease;
 511 |         height: 100%;
 512 |     }
 513 | 
 514 |     .related-article-card:hover {
 515 |         transform: translateY(-4px);
 516 |         border-color: rgba(220, 38, 38, 0.3);
 517 |         box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
 518 |     }
 519 | 
 520 |     .related-image {
 521 |         height: 160px;
 522 |         overflow: hidden;
 523 |     }
 524 | 
 525 |     .related-image img {
 526 |         width: 100%;
 527 |         height: 100%;
 528 |         object-fit: cover;
 529 |         transition: transform 0.3s ease;
 530 |     }
 531 | 
 532 |     .related-article-card:hover .related-image img {
 533 |         transform: scale(1.05);
 534 |     }
 535 | 
 536 |     .related-content {
 537 |         padding: 1.5rem;
 538 |     }
 539 | 
 540 |     .related-category {
 541 |         font-size: 0.75rem;
 542 |         font-weight: 600;
 543 |         color: #dc2626;
 544 |         text-transform: uppercase;
 545 |         letter-spacing: 0.5px;
 546 |         margin-bottom: 0.75rem;
 547 |     }
 548 | 
 549 |     .related-title {
 550 |         font-size: 1.1rem;
 551 |         font-weight: 700;
 552 |         color: #fff;
 553 |         margin-bottom: 1rem;
 554 |         line-height: 1.3;
 555 |     }
 556 | 
 557 |     .related-date {
 558 |         font-size: 0.875rem;
 559 |         color: rgba(255, 255, 255, 0.6);
 560 |     }
 561 | 
 562 |     @media (max-width: 768px) {
 563 |         .article-title-professional {
 564 |             font-size: 2rem;
 565 |         }
 566 | 
 567 |         .article-footer-professional {
 568 |             grid-template-columns: 1fr;
 569 |             gap: 2rem;
 570 |         }
 571 | 
 572 |         .share-social-section {
 573 |             flex-direction: column;
 574 |             align-items: flex-start;
 575 |         }
 576 |     }
 577 | </style>
 578 | 
 579 | <script>
 580 |     // Reading progress bar
 581 |     window.addEventListener('scroll', function() {
 582 |         const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
 583 |         const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
 584 |         const scrolled = (winScroll / height) * 100;
 585 |         document.querySelector('.reading-progress').style.width = scrolled + '%';
 586 |     });
 587 | 
 588 |     // Copy to clipboard functionality
 589 |     function copyToClipboard(text) {
 590 |         navigator.clipboard.writeText(text).then(function() {
 591 |             const toast = new bootstrap.Toast(document.getElementById('copyToast'));
 592 |             toast.show();
 593 |         });
 594 |     }
 595 | 
 596 |     // ── P3 Affiliate: Behavioral intent scoring + CTA reveal ──
 597 |     (function() {
 598 |         var ctaBlock = document.getElementById('affCtaBlock');
 599 |         if (!ctaBlock) return;
 600 | 
 601 |         var partner = ctaBlock.dataset.partner;
 602 |         var variant = ctaBlock.dataset.variant;
 603 |         var referrer = ctaBlock.dataset.referrer;
 604 |         var startTime = Date.now();
 605 |         var maxScroll = 0;
 606 |         var ctaShown = false;
 607 | 
 608 |         function getIntentScore() {
 609 |             var timeSecs = (Date.now() - startTime) / 1000;
 610 |             var timeScore = Math.min(timeSecs / 90, 1) * 40; // max 40 pts at 90s
 611 |             var scrollScore = maxScroll * 60;                 // max 60 pts at 100% scroll
 612 |             return Math.min(100, Math.round(timeScore + scrollScore));
 613 |         }
 614 | 
 615 |         function showCta() {
 616 |             if (ctaShown) return;
 617 |             ctaShown = true;
 618 |             ctaBlock.style.opacity = '1';
 619 |             // Track impression via beacon
 620 |             var payload = JSON.stringify({
 621 |                 partner: partner, variant: variant, referrer_page: referrer
 622 |             });
 623 |             if (navigator.sendBeacon) {
 624 |                 navigator.sendBeacon('/api/affiliates/impression',
 625 |                     new Blob([payload], {type: 'application/json'}));
 626 |             }
 627 |         }
 628 | 
 629 |         // Scroll tracker
 630 |         window.addEventListener('scroll', function() {
 631 |             var scrollPct = window.scrollY / (document.body.scrollHeight - window.innerHeight);
 632 |             if (scrollPct > maxScroll) maxScroll = scrollPct;
 633 |             if (getIntentScore() >= 40) showCta();
 634 |         }, {passive: true});
 635 | 
 636 |         // Time-based fallback: show after 60s regardless
 637 |         setTimeout(showCta, 60000);
 638 | 
 639 |         // IntersectionObserver for CTA block visibility
 640 |         if ('IntersectionObserver' in window) {
 641 |             var obs = new IntersectionObserver(function(entries) {
 642 |                 entries.forEach(function(e) {
 643 |                     if (e.isIntersecting && getIntentScore() >= 20) showCta();
 644 |                 });
 645 |             }, {threshold: 0.5});
 646 |             obs.observe(ctaBlock);
 647 |         }
 648 | 
 649 |         // Wire affiliate link clicks to add variant param
 650 |         ctaBlock.querySelectorAll('a.aff-card-cta, a.aff-link-inline').forEach(function(a) {
 651 |             a.addEventListener('click', function() {
 652 |                 var href = a.getAttribute('href');
 653 |                 if (href && !href.includes('?')) href += '?';
 654 |                 else if (href) href += '&';
 655 |                 a.setAttribute('href', href + 'ref=' + encodeURIComponent(referrer) + '&v=' + variant);
 656 |             });
 657 |         });
 658 |     })();
 659 | </script>
 660 | {% endblock %}
 661 | 
 662 | 
```

### File: core/templates/bitcoin_life_insurance.html (630 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Bitcoin Life Insurance — Meanwhile | Protocol Pulse{% endblock %}
   4 | {% block meta_description %}Protect your Bitcoin legacy with life insurance denominated in BTC — not fiat. Meanwhile offers self-sovereign estate planning for Bitcoiners.{% endblock %}
   5 | 
   6 | {% block og_meta %}
   7 | <meta property="og:title" content="Bitcoin Life Insurance — Meanwhile | Protocol Pulse">
   8 | <meta property="og:description" content="Death benefit in BTC. Your family inherits sovereignty, not a fiat check.">
   9 | <meta property="og:type" content="website">
  10 | {% endblock %}
  11 | 
  12 | {% block extra_css %}
  13 | <style>
  14 | /* ─── MEANWHILE LANDING PAGE ─── */
  15 | .meanwhile-page {
  16 |     background: #06070b;
  17 |     min-height: 100vh;
  18 |     color: #eef2ff;
  19 |     font-family: ui-sans-serif, system-ui, sans-serif;
  20 | }
  21 | 
  22 | /* Hero */
  23 | .mw-hero {
  24 |     position: relative;
  25 |     padding: 100px 0 80px;
  26 |     overflow: hidden;
  27 |     text-align: center;
  28 | }
  29 | .mw-hero::before {
  30 |     content: '';
  31 |     position: absolute;
  32 |     top: -120px; left: 50%;
  33 |     transform: translateX(-50%);
  34 |     width: 700px; height: 700px;
  35 |     background: radial-gradient(circle, rgba(248,193,92,0.08) 0%, transparent 70%);
  36 |     pointer-events: none;
  37 | }
  38 | .mw-hero::after {
  39 |     content: '';
  40 |     position: absolute;
  41 |     top: 0; left: 0; right: 0;
  42 |     bottom: 0;
  43 |     background: radial-gradient(ellipse 60% 50% at 20% 30%, rgba(255,59,95,0.07) 0%, transparent 60%),
  44 |                 radial-gradient(ellipse 40% 40% at 80% 20%, rgba(93,228,255,0.05) 0%, transparent 60%);
  45 |     pointer-events: none;
  46 | }
  47 | .mw-kicker {
  48 |     font-family: 'JetBrains Mono', monospace;
  49 |     font-size: 0.65rem;
  50 |     font-weight: 800;
  51 |     letter-spacing: 0.22em;
  52 |     text-transform: uppercase;
  53 |     color: #f8c15c;
  54 |     margin-bottom: 1.2rem;
  55 |     display: flex;
  56 |     align-items: center;
  57 |     justify-content: center;
  58 |     gap: 0.6rem;
  59 | }
  60 | .mw-kicker-dot {
  61 |     width: 6px; height: 6px;
  62 |     border-radius: 50%;
  63 |     background: #f8c15c;
  64 |     animation: mw-pulse 2s ease-in-out infinite;
  65 | }
  66 | @keyframes mw-pulse {
  67 |     0%, 100% { opacity: 1; transform: scale(1); }
  68 |     50% { opacity: 0.5; transform: scale(0.7); }
  69 | }
  70 | .mw-hero h1 {
  71 |     font-size: clamp(2.2rem, 5vw, 3.8rem);
  72 |     font-weight: 900;
  73 |     line-height: 1.05;
  74 |     letter-spacing: -0.04em;
  75 |     color: #eef2ff;
  76 |     max-width: 820px;
  77 |     margin: 0 auto 1.4rem;
  78 |     text-shadow: 0 4px 28px rgba(0,0,0,0.4);
  79 | }
  80 | .mw-hero h1 span { color: #f8c15c; }
  81 | .mw-hero-sub {
  82 |     font-size: 1.15rem;
  83 |     color: #95a0ba;
  84 |     max-width: 540px;
  85 |     margin: 0 auto 2.5rem;
  86 |     line-height: 1.6;
  87 | }
  88 | .mw-cta-btn {
  89 |     display: inline-flex;
  90 |     align-items: center;
  91 |     gap: 0.5rem;
  92 |     background: #ff3b5f;
  93 |     color: #fff;
  94 |     font-weight: 700;
  95 |     font-size: 1rem;
  96 |     padding: 0.85rem 2.2rem;
  97 |     border-radius: 8px;
  98 |     text-decoration: none;
  99 |     transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
 100 |     box-shadow: 0 4px 20px rgba(255,59,95,0.35);
 101 |     border: none;
 102 | }
 103 | .mw-cta-btn:hover {
 104 |     background: #e0364f;
 105 |     transform: translateY(-2px);
 106 |     box-shadow: 0 8px 32px rgba(255,59,95,0.45);
 107 |     color: #fff;
 108 |     text-decoration: none;
 109 | }
 110 | .mw-disclaimer-small {
 111 |     margin-top: 1.2rem;
 112 |     font-size: 0.72rem;
 113 |     color: #555e78;
 114 |     letter-spacing: 0.04em;
 115 | }
 116 | 
 117 | /* Why It Matters */
 118 | .mw-section { padding: 80px 0; }
 119 | .mw-section-kicker {
 120 |     font-family: 'JetBrains Mono', monospace;
 121 |     font-size: 0.62rem;
 122 |     font-weight: 800;
 123 |     letter-spacing: 0.20em;
 124 |     text-transform: uppercase;
 125 |     color: #f8c15c;
 126 |     margin-bottom: 0.8rem;
 127 | }
 128 | .mw-section-title {
 129 |     font-size: clamp(1.6rem, 3.5vw, 2.4rem);
 130 |     font-weight: 900;
 131 |     letter-spacing: -0.03em;
 132 |     color: #eef2ff;
 133 |     margin-bottom: 3rem;
 134 | }
 135 | .mw-cards {
 136 |     display: grid;
 137 |     grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
 138 |     gap: 1.5rem;
 139 | }
 140 | .mw-card {
 141 |     background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
 142 |     border: 1px solid rgba(255,255,255,0.08);
 143 |     border-left: 3px solid #f8c15c;
 144 |     border-radius: 14px;
 145 |     padding: 1.8rem;
 146 |     transition: border-color 0.2s, box-shadow 0.2s;
 147 | }
 148 | .mw-card:hover {
 149 |     border-left-color: #ff3b5f;
 150 |     box-shadow: 0 12px 36px rgba(0,0,0,0.3);
 151 | }
 152 | .mw-card-icon {
 153 |     font-size: 1.8rem;
 154 |     margin-bottom: 1rem;
 155 |     display: block;
 156 | }
 157 | .mw-card h3 {
 158 |     font-size: 1rem;
 159 |     font-weight: 700;
 160 |     color: #eef2ff;
 161 |     margin-bottom: 0.6rem;
 162 | }
 163 | .mw-card p {
 164 |     font-size: 0.9rem;
 165 |     color: #95a0ba;
 166 |     line-height: 1.6;
 167 |     margin: 0;
 168 | }
 169 | 
 170 | /* How It Works */
 171 | .mw-how-bg {
 172 |     background: linear-gradient(180deg, transparent 0%, rgba(248,193,92,0.03) 50%, transparent 100%);
 173 |     border-top: 1px solid rgba(255,255,255,0.04);
 174 |     border-bottom: 1px solid rgba(255,255,255,0.04);
 175 | }
 176 | .mw-steps {
 177 |     display: grid;
 178 |     grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
 179 |     gap: 1.5rem;
 180 |     counter-reset: step;
 181 | }
 182 | .mw-step {
 183 |     position: relative;
 184 |     padding: 1.5rem;
 185 |     background: rgba(255,255,255,0.03);
 186 |     border-radius: 12px;
 187 |     border: 1px solid rgba(255,255,255,0.06);
 188 | }
 189 | .mw-step-num {
 190 |     font-family: 'JetBrains Mono', monospace;
 191 |     font-size: 2rem;
 192 |     font-weight: 900;
 193 |     color: rgba(248,193,92,0.25);
 194 |     line-height: 1;
 195 |     margin-bottom: 0.8rem;
 196 | }
 197 | .mw-step h4 {
 198 |     font-size: 0.95rem;
 199 |     font-weight: 700;
 200 |     color: #eef2ff;
 201 |     margin-bottom: 0.4rem;
 202 | }
 203 | .mw-step p {
 204 |     font-size: 0.85rem;
 205 |     color: #95a0ba;
 206 |     margin: 0;
 207 |     line-height: 1.5;
 208 | }
 209 | 
 210 | /* Editorial */
 211 | .mw-editorial {
 212 |     background: rgba(255,255,255,0.02);
 213 |     border: 1px solid rgba(255,255,255,0.06);
 214 |     border-radius: 20px;
 215 |     padding: 3rem;
 216 |     position: relative;
 217 | }
 218 | .mw-editorial::before {
 219 |     content: '"';
 220 |     position: absolute;
 221 |     top: 1.5rem; left: 2rem;
 222 |     font-size: 6rem;
 223 |     line-height: 1;
 224 |     color: rgba(248,193,92,0.12);
 225 |     font-family: Georgia, serif;
 226 |     pointer-events: none;
 227 | }
 228 | .mw-editorial-byline {
 229 |     display: flex;
 230 |     align-items: center;
 231 |     gap: 1rem;
 232 |     margin-bottom: 1.8rem;
 233 | }
 234 | .mw-editorial-avatar {
 235 |     width: 48px; height: 48px;
 236 |     border-radius: 50%;
 237 |     background: linear-gradient(135deg, #ff3b5f, #f8c15c);
 238 |     display: flex; align-items: center; justify-content: center;
 239 |     font-size: 1.2rem; font-weight: 900; color: #fff;
 240 |     flex-shrink: 0;
 241 | }
 242 | .mw-editorial-author {
 243 |     font-weight: 700;
 244 |     color: #eef2ff;
 245 |     font-size: 0.95rem;
 246 | }
 247 | .mw-editorial-role {
 248 |     font-size: 0.8rem;
 249 |     color: #95a0ba;
 250 |     margin-top: 0.15rem;
 251 | }
 252 | .mw-editorial p {
 253 |     font-size: 1.05rem;
 254 |     color: #c8d0e8;
 255 |     line-height: 1.75;
 256 |     margin-bottom: 1.2rem;
 257 | }
 258 | .mw-editorial p:last-of-type { margin-bottom: 0; }
 259 | .mw-affiliate-badge {
 260 |     display: inline-flex;
 261 |     align-items: center;
 262 |     gap: 0.4rem;
 263 |     font-family: 'JetBrains Mono', monospace;
 264 |     font-size: 0.62rem;
 265 |     font-weight: 800;
 266 |     letter-spacing: 0.12em;
 267 |     text-transform: uppercase;
 268 |     background: rgba(248,193,92,0.08);
 269 |     border: 1px solid rgba(248,193,92,0.20);
 270 |     color: #f8c15c;
 271 |     padding: 0.3rem 0.8rem;
 272 |     border-radius: 999px;
 273 |     margin-top: 1.5rem;
 274 | }
 275 | 
 276 | /* Sovereignty Score */
 277 | .mw-sov-score {
 278 |     background: rgba(255,255,255,0.03);
 279 |     border: 1px solid rgba(255,255,255,0.08);
 280 |     border-radius: 16px;
 281 |     padding: 2rem;
 282 |     margin-top: 3rem;
 283 | }
 284 | .mw-sov-title {
 285 |     font-family: 'JetBrains Mono', monospace;
 286 |     font-size: 0.65rem;
 287 |     font-weight: 800;
 288 |     letter-spacing: 0.18em;
 289 |     text-transform: uppercase;
 290 |     color: #f8c15c;
 291 |     margin-bottom: 1.2rem;
 292 | }
 293 | .mw-sov-rows { display: flex; flex-direction: column; gap: 0.7rem; }
 294 | .mw-sov-row {
 295 |     display: flex;
 296 |     align-items: center;
 297 |     gap: 1rem;
 298 | }
 299 | .mw-sov-label {
 300 |     font-size: 0.8rem;
 301 |     color: #95a0ba;
 302 |     width: 130px;
 303 |     flex-shrink: 0;
 304 | }
 305 | .mw-sov-bars {
 306 |     display: flex;
 307 |     gap: 4px;
 308 | }
 309 | .mw-sov-bar {
 310 |     width: 18px; height: 10px;
 311 |     border-radius: 3px;
 312 |     background: rgba(255,255,255,0.06);
 313 |     border: 1px solid rgba(255,255,255,0.08);
 314 | }
 315 | .mw-sov-bar.filled { background: #f8c15c; border-color: #f8c15c; }
 316 | 
 317 | /* FAQ */
 318 | .mw-faq { display: flex; flex-direction: column; gap: 0.8rem; }
 319 | .mw-faq-item {
 320 |     background: rgba(255,255,255,0.03);
 321 |     border: 1px solid rgba(255,255,255,0.07);
 322 |     border-radius: 12px;
 323 |     overflow: hidden;
 324 | }
 325 | .mw-faq-q {
 326 |     width: 100%;
 327 |     background: none;
 328 |     border: none;
 329 |     padding: 1.2rem 1.5rem;
 330 |     text-align: left;
 331 |     color: #eef2ff;
 332 |     font-size: 0.95rem;
 333 |     font-weight: 600;
 334 |     cursor: pointer;
 335 |     display: flex;
 336 |     justify-content: space-between;
 337 |     align-items: center;
 338 |     gap: 1rem;
 339 |     transition: color 0.2s;
 340 | }
 341 | .mw-faq-q:hover { color: #f8c15c; }
 342 | .mw-faq-q::after {
 343 |     content: '+';
 344 |     font-size: 1.2rem;
 345 |     font-weight: 300;
 346 |     color: #f8c15c;
 347 |     flex-shrink: 0;
 348 |     transition: transform 0.2s;
 349 | }
 350 | .mw-faq-item.open .mw-faq-q::after { content: '−'; }
 351 | .mw-faq-a {
 352 |     display: none;
 353 |     padding: 0 1.5rem 1.2rem;
 354 |     font-size: 0.9rem;
 355 |     color: #95a0ba;
 356 |     line-height: 1.7;
 357 |     border-top: 1px solid rgba(255,255,255,0.05);
 358 | }
 359 | .mw-faq-item.open .mw-faq-a { display: block; }
 360 | 
 361 | /* CTA Footer */
 362 | .mw-cta-footer {
 363 |     text-align: center;
 364 |     padding: 80px 0;
 365 |     background: linear-gradient(180deg, transparent 0%, rgba(255,59,95,0.04) 50%, transparent 100%);
 366 | }
 367 | .mw-cta-footer h2 {
 368 |     font-size: clamp(1.8rem, 4vw, 3rem);
 369 |     font-weight: 900;
 370 |     letter-spacing: -0.03em;
 371 |     color: #eef2ff;
 372 |     margin-bottom: 1rem;
 373 | }
 374 | .mw-cta-footer p {
 375 |     color: #95a0ba;
 376 |     font-size: 1.05rem;
 377 |     margin-bottom: 2rem;
 378 | }
 379 | .mw-disclaimer {
 380 |     font-size: 0.75rem;
 381 |     color: #444e66;
 382 |     max-width: 500px;
 383 |     margin: 1.5rem auto 0;
 384 |     line-height: 1.6;
 385 | }
 386 | 
 387 | /* Responsive */
 388 | @media (max-width: 768px) {
 389 |     .mw-hero { padding: 70px 0 60px; }
 390 |     .mw-editorial { padding: 1.8rem; }
 391 |     .mw-editorial::before { display: none; }
 392 |     .mw-section { padding: 56px 0; }
 393 | }
 394 | </style>
 395 | {% endblock %}
 396 | 
 397 | {% block content %}
 398 | <div class="meanwhile-page">
 399 | 
 400 |   <!-- HERO -->
 401 |   <section class="mw-hero">
 402 |     <div class="container">
 403 |       <div class="mw-kicker">
 404 |         <span class="mw-kicker-dot"></span>
 405 |         AFFILIATE PARTNERSHIP &nbsp;•&nbsp; BITCOIN SOVEREIGN TOOLS
 406 |       </div>
 407 |       <h1>Your Bitcoin Legacy<br>Deserves <span>Protection</span></h1>
 408 |       <p class="mw-hero-sub">
 409 |         Life insurance denominated in Bitcoin — not fiat. Not stocks.
 410 |         <strong>Bitcoin.</strong> Your family inherits sovereignty, not a check.
 411 |       </p>
 412 |       <a href="/go/meanwhile?ref=/bitcoin-life-insurance&v=hero"
 413 |          class="mw-cta-btn"
 414 |          data-partner="meanwhile"
 415 |          onclick="trackAffClick('meanwhile','hero')">
 416 |         Get Your Quote →
 417 |       </a>
 418 |       <p class="mw-disclaimer-small">
 419 |         Affiliate partnership. Not financial advice. See disclaimer below.
 420 |       </p>
 421 |     </div>
 422 |   </section>
 423 | 
 424 |   <!-- WHY IT MATTERS -->
 425 |   <section class="mw-section">
 426 |     <div class="container">
 427 |       <div class="mw-section-kicker">Why Bitcoiners Choose Meanwhile</div>
 428 |       <h2 class="mw-section-title">Protect Your Stack. Protect Your Family.</h2>
 429 |       <div class="mw-cards">
 430 |         <div class="mw-card">
 431 |           <span class="mw-card-icon">₿</span>
 432 |           <h3>Death benefit in BTC</h3>
 433 |           <p>Your family inherits sovereignty — a Bitcoin-denominated benefit, not a fiat check subject to monetary debasement.</p>
 434 |         </div>
 435 |         <div class="mw-card">
 436 |           <span class="mw-card-icon">🛡</span>
 437 |           <h3>No fiat conversion risk</h3>
 438 |           <p>The benefit doesn't lose purchasing power. Denominated and paid in Bitcoin. No forced liquidation at inopportune times.</p>
 439 |         </div>
 440 |         <div class="mw-card">
 441 |           <span class="mw-card-icon">🔑</span>
 442 |           <h3>Self-sovereign planning</h3>
 443 |           <p>Outside the traditional insurance industry's fiat-first assumptions. Designed specifically for Bitcoiners who think in sats.</p>
 444 |         </div>
 445 |       </div>
 446 |     </div>
 447 |   </section>
 448 | 
 449 |   <!-- HOW IT WORKS -->
 450 |   <section class="mw-section mw-how-bg">
 451 |     <div class="container">
 452 |       <div class="mw-section-kicker">How Meanwhile Works</div>
 453 |       <h2 class="mw-section-title">From Application to Coverage</h2>
 454 |       <div class="mw-steps">
 455 |         <div class="mw-step">
 456 |           <div class="mw-step-num">01</div>
 457 |           <h4>Apply online</h4>
 458 |           <p>Full application process online. No in-person meetings required.</p>
 459 |         </div>
 460 |         <div class="mw-step">
 461 |           <div class="mw-step-num">02</div>
 462 |           <h4>Whole life product</h4>
 463 |           <p>BTC-denominated whole life insurance policy from a regulated insurer.</p>
 464 |         </div>
 465 |         <div class="mw-step">
 466 |           <div class="mw-step-num">03</div>
 467 |           <h4>BTC-denominated policy</h4>
 468 |           <p>Policy value tracked in Bitcoin from day one. No fiat intermediary.</p>
 469 |         </div>
 470 |         <div class="mw-step">
 471 |           <div class="mw-step-num">04</div>
 472 |           <h4>Benefit paid in BTC</h4>
 473 |           <p>Death benefit paid directly to a Bitcoin wallet. Sovereign inheritance.</p>
 474 |         </div>
 475 |       </div>
 476 |     </div>
 477 |   </section>
 478 | 
 479 |   <!-- EDITORIAL ENDORSEMENT -->
 480 |   <section class="mw-section">
 481 |     <div class="container">
 482 |       <div class="mw-section-kicker">Protocol Pulse Perspective</div>
 483 |       <h2 class="mw-section-title">Why We Partner With Meanwhile</h2>
 484 |       <div class="mw-editorial">
 485 |         <div class="mw-editorial-byline">
 486 |           <div class="mw-editorial-avatar">PP</div>
 487 |           <div>
 488 |             <div class="mw-editorial-author">Protocol Pulse Editorial</div>
 489 |             <div class="mw-editorial-role">Intelligence for Transactors</div>
 490 |           </div>
 491 |         </div>
 492 |         <p>
 493 |           Most Bitcoiners think about sovereignty in terms of keys and custody.
 494 |           But there's a dimension of sovereignty almost no one addresses: generational
 495 |           transfer. What happens to your stack when you're gone? If the answer is
 496 |           "my family figures it out," that's not a plan — that's a fiat outcome
 497 |           dressed up in orange coin.
 498 |         </p>
 499 |         <p>
 500 |           Meanwhile solves a real problem. Life insurance that pays out in Bitcoin,
 501 |           denominated in Bitcoin, without forcing your family to sell into a fiat
 502 |           intermediary to receive a "benefit" that's actually a debasement-adjusted
 503 |           fraction of what you earned. This is what sovereignty looks like extended
 504 |           across time — not just across border.
 505 |         </p>
 506 |         <p>
 507 |           We vetted Meanwhile before partnering. The product is real, the insurer is
 508 |           regulated, and the Bitcoin-native architecture is genuine. For Bitcoiners
 509 |           with dependents and meaningful stacks, this isn't a financial product —
 510 |           it's a cypherpunk responsibility. We stand behind this.
 511 |         </p>
 512 |         <div class="mw-affiliate-badge">
 513 |           ⚡ Affiliate Partnership — We earn a commission if you apply through our link.
 514 |           This is not financial advice.
 515 |         </div>
 516 |       </div>
 517 | 
 518 |       <!-- Sovereignty Score -->
 519 |       <div class="mw-sov-score">
 520 |         <div class="mw-sov-title">Protocol Pulse Sovereignty Score — Meanwhile</div>
 521 |         <div class="mw-sov-rows">
 522 |           {% set scores = [
 523 |             ('Privacy', 4),
 524 |             ('BTC-Native Architecture', 5),
 525 |             ('Non-Custodial Structure', 3),
 526 |             ('Regulatory Compliance', 4),
 527 |             ('Transparency', 4)
 528 |           ] %}
 529 |           {% for label, score in scores %}
 530 |           <div class="mw-sov-row">
 531 |             <span class="mw-sov-label">{{ label }}</span>
 532 |             <div class="mw-sov-bars">
 533 |               {% for i in range(1, 6) %}
 534 |               <div class="mw-sov-bar {% if i <= score %}filled{% endif %}"></div>
 535 |               {% endfor %}
 536 |             </div>
 537 |             <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#f8c15c;font-weight:700;">{{ score }}/5</span>
 538 |           </div>
 539 |           {% endfor %}
 540 |         </div>
 541 |       </div>
 542 |     </div>
 543 |   </section>
 544 | 
 545 |   <!-- FAQ -->
 546 |   <section class="mw-section mw-how-bg">
 547 |     <div class="container">
 548 |       <div class="mw-section-kicker">Common Questions</div>
 549 |       <h2 class="mw-section-title">FAQ</h2>
 550 |       <div class="mw-faq" style="max-width:740px;">
 551 |         {% set faqs = [
 552 |           ("Who is Meanwhile?",
 553 |            "Meanwhile is a life insurance company designed specifically for the Bitcoin economy. Founded by Bitcoiners, for Bitcoiners. They offer whole life insurance products denominated and payable in Bitcoin."),
 554 |           ("Is this regulated?",
 555 |            "Yes. Meanwhile works with regulated insurance carriers. The product operates under existing life insurance regulatory frameworks while being structured to pay benefits in Bitcoin."),
 556 |           ("How is the benefit paid?",
 557 |            "The death benefit is paid directly in Bitcoin to the wallet address designated in the policy. No fiat conversion required unless the beneficiary chooses it."),
 558 |           ("What happens to the BTC if the price drops?",
 559 |            "The policy is denominated in Bitcoin, not USD. If Bitcoin's price in fiat terms drops, the Bitcoin amount is unaffected. This is a feature for those who measure wealth in sats, not dollars."),
 560 |           ("Is there a medical exam?",
 561 |            "Meanwhile's application process varies by coverage amount. Smaller policies may not require a medical exam. The application is handled entirely online."),
 562 |           ("What coverage amounts are available?",
 563 |            "Coverage amounts vary based on the applicant's profile. Visit Meanwhile's site through our link for current availability and to get a personalized quote."),
 564 |         ] %}
 565 |         {% for q, a in faqs %}
 566 |         <div class="mw-faq-item">
 567 |           <button class="mw-faq-q" onclick="toggleFaq(this)">{{ q }}</button>
 568 |           <div class="mw-faq-a">{{ a }}</div>
 569 |         </div>
 570 |         {% endfor %}
 571 |       </div>
 572 |     </div>
 573 |   </section>
 574 | 
 575 |   <!-- CTA FOOTER -->
 576 |   <section class="mw-cta-footer">
 577 |     <div class="container">
 578 |       <div class="mw-section-kicker" style="justify-content:center;">Take Action</div>
 579 |       <h2>Start Your Application</h2>
 580 |       <p>Protect your Bitcoin legacy. Your family's sovereignty depends on it.</p>
 581 |       <a href="/go/meanwhile?ref=/bitcoin-life-insurance&v=footer"
 582 |          class="mw-cta-btn"
 583 |          data-partner="meanwhile"
 584 |          onclick="trackAffClick('meanwhile','footer')"
 585 |          style="font-size:1.1rem;padding:1rem 2.8rem;">
 586 |         Get Your Quote →
 587 |       </a>
 588 |       <p class="mw-disclaimer">
 589 |         Protocol Pulse may earn compensation when you apply through our link.
 590 |         This is not financial advice. Insurance products are subject to availability
 591 |         and eligibility requirements. Review all policy terms with Meanwhile directly.
 592 |       </p>
 593 |     </div>
 594 |   </section>
 595 | 
 596 | </div>
 597 | {% endblock %}
 598 | 
 599 | {% block extra_js %}
 600 | <script>
 601 | // FAQ toggle
 602 | function toggleFaq(btn) {
 603 |     const item = btn.closest('.mw-faq-item');
 604 |     item.classList.toggle('open');
 605 |     btn.setAttribute('aria-expanded', item.classList.contains('open'));
 606 | }
 607 | 
 608 | // Affiliate click tracking (non-blocking)
 609 | function trackAffClick(partner, placement) {
 610 |     const payload = JSON.stringify({
 611 |         partner: partner,
 612 |         variant: 'B',
 613 |         referrer_page: window.location.pathname + '?placement=' + placement
 614 |     });
 615 |     if (navigator.sendBeacon) {
 616 |         navigator.sendBeacon('/api/affiliates/impression', new Blob([payload], {type:'application/json'}));
 617 |     }
 618 | }
 619 | 
 620 | // Keyboard nav for FAQ
 621 | document.querySelectorAll('.mw-faq-q').forEach(function(btn, i, all) {
 622 |     btn.setAttribute('aria-expanded', 'false');
 623 |     btn.addEventListener('keydown', function(e) {
 624 |         if (e.key === 'ArrowDown' && all[i+1]) { all[i+1].focus(); e.preventDefault(); }
 625 |         if (e.key === 'ArrowUp' && all[i-1]) { all[i-1].focus(); e.preventDefault(); }
 626 |     });
 627 | });
 628 | </script>
 629 | {% endblock %}
 630 | 
```

### File: core/templates/digital_residency.html (650 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Palau Digital Residency — RNS.ID | Protocol Pulse{% endblock %}
   4 | {% block meta_description %}Establish your digital sovereignty with a Palau Digital Residency via RNS.ID. Government-issued digital ID outside the financial surveillance state.{% endblock %}
   5 | 
   6 | {% block og_meta %}
   7 | <meta property="og:title" content="Palau Digital Residency — RNS.ID | Protocol Pulse">
   8 | <meta property="og:description" content="A government-issued digital identity outside the surveillance state. Digital sovereignty starts with ID.">
   9 | <meta property="og:type" content="website">
  10 | {% endblock %}
  11 | 
  12 | {% block extra_css %}
  13 | <style>
  14 | /* ─── RNS.ID DIGITAL RESIDENCY LANDING PAGE ─── */
  15 | .rns-page {
  16 |     background: #06070b;
  17 |     min-height: 100vh;
  18 |     color: #eef2ff;
  19 |     font-family: ui-sans-serif, system-ui, sans-serif;
  20 | }
  21 | 
  22 | /* Accent: green for RNS.ID (freedom/sovereignty signal) */
  23 | :root {
  24 |     --rns-green: #00d68f;
  25 |     --rns-green-dim: rgba(0,214,143,0.08);
  26 |     --rns-green-border: rgba(0,214,143,0.22);
  27 | }
  28 | 
  29 | /* Hero */
  30 | .rns-hero {
  31 |     position: relative;
  32 |     padding: 100px 0 80px;
  33 |     overflow: hidden;
  34 |     text-align: center;
  35 | }
  36 | .rns-hero::before {
  37 |     content: '';
  38 |     position: absolute;
  39 |     top: -80px; left: 50%;
  40 |     transform: translateX(-50%);
  41 |     width: 700px; height: 700px;
  42 |     background: radial-gradient(circle, rgba(0,214,143,0.06) 0%, transparent 70%);
  43 |     pointer-events: none;
  44 | }
  45 | .rns-hero::after {
  46 |     content: '';
  47 |     position: absolute;
  48 |     inset: 0;
  49 |     background: radial-gradient(ellipse 60% 50% at 20% 30%, rgba(255,59,95,0.06) 0%, transparent 60%),
  50 |                 radial-gradient(ellipse 40% 40% at 80% 20%, rgba(93,228,255,0.04) 0%, transparent 60%);
  51 |     pointer-events: none;
  52 | }
  53 | 
  54 | .rns-kicker {
  55 |     font-family: 'JetBrains Mono', monospace;
  56 |     font-size: 0.65rem;
  57 |     font-weight: 800;
  58 |     letter-spacing: 0.22em;
  59 |     text-transform: uppercase;
  60 |     color: var(--rns-green);
  61 |     margin-bottom: 1.2rem;
  62 |     display: flex;
  63 |     align-items: center;
  64 |     justify-content: center;
  65 |     gap: 0.6rem;
  66 | }
  67 | .rns-kicker-dot {
  68 |     width: 6px; height: 6px;
  69 |     border-radius: 50%;
  70 |     background: var(--rns-green);
  71 |     animation: rns-pulse 2s ease-in-out infinite;
  72 | }
  73 | @keyframes rns-pulse {
  74 |     0%, 100% { opacity: 1; transform: scale(1); }
  75 |     50% { opacity: 0.4; transform: scale(0.6); }
  76 | }
  77 | 
  78 | .rns-hero h1 {
  79 |     font-size: clamp(2.2rem, 5vw, 3.8rem);
  80 |     font-weight: 900;
  81 |     line-height: 1.05;
  82 |     letter-spacing: -0.04em;
  83 |     color: #eef2ff;
  84 |     max-width: 820px;
  85 |     margin: 0 auto 1.4rem;
  86 |     text-shadow: 0 4px 28px rgba(0,0,0,0.4);
  87 | }
  88 | .rns-hero h1 span { color: var(--rns-green); }
  89 | .rns-hero-sub {
  90 |     font-size: 1.15rem;
  91 |     color: #95a0ba;
  92 |     max-width: 540px;
  93 |     margin: 0 auto 2.5rem;
  94 |     line-height: 1.6;
  95 | }
  96 | 
  97 | .rns-cta-btn {
  98 |     display: inline-flex;
  99 |     align-items: center;
 100 |     gap: 0.5rem;
 101 |     background: var(--rns-green);
 102 |     color: #06070b;
 103 |     font-weight: 800;
 104 |     font-size: 1rem;
 105 |     padding: 0.85rem 2.2rem;
 106 |     border-radius: 8px;
 107 |     text-decoration: none;
 108 |     transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
 109 |     box-shadow: 0 4px 20px rgba(0,214,143,0.30);
 110 |     border: none;
 111 | }
 112 | .rns-cta-btn:hover {
 113 |     background: #00c07d;
 114 |     transform: translateY(-2px);
 115 |     box-shadow: 0 8px 32px rgba(0,214,143,0.40);
 116 |     color: #06070b;
 117 |     text-decoration: none;
 118 | }
 119 | .rns-disclaimer-small {
 120 |     margin-top: 1.2rem;
 121 |     font-size: 0.72rem;
 122 |     color: #555e78;
 123 |     letter-spacing: 0.04em;
 124 | }
 125 | 
 126 | /* Sections */
 127 | .rns-section { padding: 80px 0; }
 128 | .rns-section-kicker {
 129 |     font-family: 'JetBrains Mono', monospace;
 130 |     font-size: 0.62rem;
 131 |     font-weight: 800;
 132 |     letter-spacing: 0.20em;
 133 |     text-transform: uppercase;
 134 |     color: var(--rns-green);
 135 |     margin-bottom: 0.8rem;
 136 | }
 137 | .rns-section-title {
 138 |     font-size: clamp(1.6rem, 3.5vw, 2.4rem);
 139 |     font-weight: 900;
 140 |     letter-spacing: -0.03em;
 141 |     color: #eef2ff;
 142 |     margin-bottom: 3rem;
 143 | }
 144 | 
 145 | /* What Is section */
 146 | .rns-what-bg {
 147 |     background: linear-gradient(180deg, transparent 0%, var(--rns-green-dim) 50%, transparent 100%);
 148 |     border-top: 1px solid rgba(255,255,255,0.04);
 149 |     border-bottom: 1px solid rgba(255,255,255,0.04);
 150 | }
 151 | .rns-what-grid {
 152 |     display: grid;
 153 |     grid-template-columns: 1fr 1fr;
 154 |     gap: 4rem;
 155 |     align-items: center;
 156 | }
 157 | @media (max-width: 768px) { .rns-what-grid { grid-template-columns: 1fr; gap: 2rem; } }
 158 | 
 159 | .rns-passport {
 160 |     background: linear-gradient(135deg, #0d1118 0%, #121824 100%);
 161 |     border: 1px solid var(--rns-green-border);
 162 |     border-radius: 20px;
 163 |     padding: 2.5rem 2rem;
 164 |     position: relative;
 165 |     overflow: hidden;
 166 | }
 167 | .rns-passport::before {
 168 |     content: '';
 169 |     position: absolute;
 170 |     top: 0; left: 0; right: 0;
 171 |     height: 4px;
 172 |     background: linear-gradient(90deg, var(--rns-green), rgba(0,214,143,0.3));
 173 | }
 174 | .rns-passport-flag {
 175 |     font-size: 2.5rem;
 176 |     margin-bottom: 1rem;
 177 |     display: block;
 178 | }
 179 | .rns-passport h3 {
 180 |     font-size: 1.2rem;
 181 |     font-weight: 800;
 182 |     color: #eef2ff;
 183 |     margin-bottom: 0.4rem;
 184 | }
 185 | .rns-passport-sub {
 186 |     font-size: 0.8rem;
 187 |     color: var(--rns-green);
 188 |     font-family: 'JetBrains Mono', monospace;
 189 |     font-weight: 700;
 190 |     letter-spacing: 0.10em;
 191 |     margin-bottom: 1.5rem;
 192 | }
 193 | .rns-passport-row {
 194 |     display: flex;
 195 |     justify-content: space-between;
 196 |     align-items: center;
 197 |     padding: 0.6rem 0;
 198 |     border-bottom: 1px solid rgba(255,255,255,0.05);
 199 |     font-size: 0.85rem;
 200 | }
 201 | .rns-passport-row:last-child { border-bottom: none; }
 202 | .rns-passport-key { color: #95a0ba; }
 203 | .rns-passport-val { color: #eef2ff; font-weight: 600; }
 204 | 
 205 | .rns-what-points { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 1rem; }
 206 | .rns-what-point {
 207 |     display: flex;
 208 |     align-items: flex-start;
 209 |     gap: 1rem;
 210 |     font-size: 0.95rem;
 211 |     color: #c8d0e8;
 212 |     line-height: 1.6;
 213 | }
 214 | .rns-point-icon {
 215 |     flex-shrink: 0;
 216 |     width: 28px; height: 28px;
 217 |     border-radius: 50%;
 218 |     background: var(--rns-green-dim);
 219 |     border: 1px solid var(--rns-green-border);
 220 |     display: flex; align-items: center; justify-content: center;
 221 |     font-size: 0.8rem;
 222 |     color: var(--rns-green);
 223 |     font-weight: 800;
 224 |     margin-top: 0.1rem;
 225 | }
 226 | 
 227 | /* Why Bitcoiners Care */
 228 | .rns-cards {
 229 |     display: grid;
 230 |     grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
 231 |     gap: 1.5rem;
 232 | }
 233 | .rns-card {
 234 |     background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
 235 |     border: 1px solid rgba(255,255,255,0.07);
 236 |     border-left: 3px solid var(--rns-green);
 237 |     border-radius: 14px;
 238 |     padding: 1.8rem;
 239 |     transition: box-shadow 0.2s, border-left-color 0.2s;
 240 | }
 241 | .rns-card:hover {
 242 |     border-left-color: #ff3b5f;
 243 |     box-shadow: 0 12px 36px rgba(0,0,0,0.3);
 244 | }
 245 | .rns-card-icon {
 246 |     font-size: 1.8rem;
 247 |     margin-bottom: 0.9rem;
 248 |     display: block;
 249 | }
 250 | .rns-card h3 { font-size: 1rem; font-weight: 700; color: #eef2ff; margin-bottom: 0.5rem; }
 251 | .rns-card p { font-size: 0.88rem; color: #95a0ba; line-height: 1.6; margin: 0; }
 252 | 
 253 | /* Editorial */
 254 | .rns-editorial {
 255 |     background: rgba(255,255,255,0.02);
 256 |     border: 1px solid rgba(255,255,255,0.06);
 257 |     border-radius: 20px;
 258 |     padding: 3rem;
 259 |     position: relative;
 260 | }
 261 | .rns-editorial::before {
 262 |     content: '"';
 263 |     position: absolute;
 264 |     top: 1.5rem; left: 2rem;
 265 |     font-size: 6rem;
 266 |     line-height: 1;
 267 |     color: rgba(0,214,143,0.10);
 268 |     font-family: Georgia, serif;
 269 |     pointer-events: none;
 270 | }
 271 | .rns-editorial-byline {
 272 |     display: flex;
 273 |     align-items: center;
 274 |     gap: 1rem;
 275 |     margin-bottom: 1.8rem;
 276 | }
 277 | .rns-editorial-avatar {
 278 |     width: 48px; height: 48px;
 279 |     border-radius: 50%;
 280 |     background: linear-gradient(135deg, #ff3b5f, var(--rns-green));
 281 |     display: flex; align-items: center; justify-content: center;
 282 |     font-size: 1.2rem; font-weight: 900; color: #fff;
 283 |     flex-shrink: 0;
 284 | }
 285 | .rns-editorial-author { font-weight: 700; color: #eef2ff; font-size: 0.95rem; }
 286 | .rns-editorial-role { font-size: 0.8rem; color: #95a0ba; margin-top: 0.15rem; }
 287 | .rns-editorial p { font-size: 1.05rem; color: #c8d0e8; line-height: 1.75; margin-bottom: 1.2rem; }
 288 | .rns-editorial p:last-of-type { margin-bottom: 0; }
 289 | 
 290 | .rns-affiliate-badge {
 291 |     display: inline-flex;
 292 |     align-items: center;
 293 |     gap: 0.4rem;
 294 |     font-family: 'JetBrains Mono', monospace;
 295 |     font-size: 0.62rem;
 296 |     font-weight: 800;
 297 |     letter-spacing: 0.12em;
 298 |     text-transform: uppercase;
 299 |     background: var(--rns-green-dim);
 300 |     border: 1px solid var(--rns-green-border);
 301 |     color: var(--rns-green);
 302 |     padding: 0.3rem 0.8rem;
 303 |     border-radius: 999px;
 304 |     margin-top: 1.5rem;
 305 | }
 306 | 
 307 | /* Sovereignty Score */
 308 | .rns-sov-score {
 309 |     background: rgba(255,255,255,0.03);
 310 |     border: 1px solid rgba(255,255,255,0.08);
 311 |     border-radius: 16px;
 312 |     padding: 2rem;
 313 |     margin-top: 3rem;
 314 | }
 315 | .rns-sov-title {
 316 |     font-family: 'JetBrains Mono', monospace;
 317 |     font-size: 0.65rem;
 318 |     font-weight: 800;
 319 |     letter-spacing: 0.18em;
 320 |     text-transform: uppercase;
 321 |     color: var(--rns-green);
 322 |     margin-bottom: 1.2rem;
 323 | }
 324 | .rns-sov-rows { display: flex; flex-direction: column; gap: 0.7rem; }
 325 | .rns-sov-row { display: flex; align-items: center; gap: 1rem; }
 326 | .rns-sov-label { font-size: 0.8rem; color: #95a0ba; width: 165px; flex-shrink: 0; }
 327 | .rns-sov-bars { display: flex; gap: 4px; }
 328 | .rns-sov-bar {
 329 |     width: 18px; height: 10px;
 330 |     border-radius: 3px;
 331 |     background: rgba(255,255,255,0.06);
 332 |     border: 1px solid rgba(255,255,255,0.08);
 333 | }
 334 | .rns-sov-bar.filled { background: var(--rns-green); border-color: var(--rns-green); }
 335 | 
 336 | /* FAQ */
 337 | .rns-faq { display: flex; flex-direction: column; gap: 0.8rem; }
 338 | .rns-faq-item {
 339 |     background: rgba(255,255,255,0.03);
 340 |     border: 1px solid rgba(255,255,255,0.07);
 341 |     border-radius: 12px;
 342 |     overflow: hidden;
 343 | }
 344 | .rns-faq-q {
 345 |     width: 100%; background: none; border: none;
 346 |     padding: 1.2rem 1.5rem; text-align: left;
 347 |     color: #eef2ff; font-size: 0.95rem; font-weight: 600;
 348 |     cursor: pointer; display: flex; justify-content: space-between;
 349 |     align-items: center; gap: 1rem; transition: color 0.2s;
 350 | }
 351 | .rns-faq-q:hover { color: var(--rns-green); }
 352 | .rns-faq-q::after { content: '+'; font-size: 1.2rem; font-weight: 300; color: var(--rns-green); flex-shrink: 0; transition: transform 0.2s; }
 353 | .rns-faq-item.open .rns-faq-q::after { content: '−'; }
 354 | .rns-faq-a {
 355 |     display: none; padding: 0 1.5rem 1.2rem;
 356 |     font-size: 0.9rem; color: #95a0ba; line-height: 1.7;
 357 |     border-top: 1px solid rgba(255,255,255,0.05);
 358 | }
 359 | .rns-faq-item.open .rns-faq-a { display: block; }
 360 | 
 361 | /* CTA Footer */
 362 | .rns-cta-footer {
 363 |     text-align: center;
 364 |     padding: 80px 0;
 365 |     background: linear-gradient(180deg, transparent 0%, var(--rns-green-dim) 50%, transparent 100%);
 366 | }
 367 | .rns-cta-footer h2 {
 368 |     font-size: clamp(1.8rem, 4vw, 3rem);
 369 |     font-weight: 900;
 370 |     letter-spacing: -0.03em;
 371 |     color: #eef2ff;
 372 |     margin-bottom: 1rem;
 373 | }
 374 | .rns-cta-footer p { color: #95a0ba; font-size: 1.05rem; margin-bottom: 2rem; }
 375 | .rns-disclaimer {
 376 |     font-size: 0.75rem;
 377 |     color: #444e66;
 378 |     max-width: 500px;
 379 |     margin: 1.5rem auto 0;
 380 |     line-height: 1.6;
 381 | }
 382 | 
 383 | @media (max-width: 768px) {
 384 |     .rns-hero { padding: 70px 0 60px; }
 385 |     .rns-editorial { padding: 1.8rem; }
 386 |     .rns-editorial::before { display: none; }
 387 |     .rns-section { padding: 56px 0; }
 388 | }
 389 | </style>
 390 | {% endblock %}
 391 | 
 392 | {% block content %}
 393 | <div class="rns-page">
 394 | 
 395 |   <!-- HERO -->
 396 |   <section class="rns-hero">
 397 |     <div class="container">
 398 |       <div class="rns-kicker">
 399 |         <span class="rns-kicker-dot"></span>
 400 |         AFFILIATE PARTNERSHIP &nbsp;•&nbsp; DIGITAL SOVEREIGNTY TOOLS
 401 |       </div>
 402 |       <h1>Establish Your<br><span>Digital Sovereignty</span></h1>
 403 |       <p class="rns-hero-sub">
 404 |         A government-issued digital ID outside the traditional financial
 405 |         surveillance state. <strong>Palau Digital Residency via RNS.ID.</strong>
 406 |       </p>
 407 |       <a href="/go/rns?ref=/digital-residency&v=hero"
 408 |          class="rns-cta-btn"
 409 |          data-partner="rns_id"
 410 |          onclick="trackAffClick('rns_id','hero')">
 411 |         Apply Now →
 412 |       </a>
 413 |       <p class="rns-disclaimer-small">
 414 |         Affiliate partnership. Not legal or financial advice. See disclaimer below.
 415 |       </p>
 416 |     </div>
 417 |   </section>
 418 | 
 419 |   <!-- WHAT IS IT -->
 420 |   <section class="rns-section rns-what-bg">
 421 |     <div class="container">
 422 |       <div class="rns-section-kicker">The Product</div>
 423 |       <h2 class="rns-section-title">What Is Palau Digital Residency?</h2>
 424 |       <div class="rns-what-grid">
 425 |         <div class="rns-passport">
 426 |           <span class="rns-passport-flag">🇵🇼</span>
 427 |           <h3>Republic of Palau</h3>
 428 |           <div class="rns-passport-sub">DIGITAL RESIDENT CERTIFICATE</div>
 429 |           <div class="rns-passport-row">
 430 |             <span class="rns-passport-key">Issuing Authority</span>
 431 |             <span class="rns-passport-val">Republic of Palau</span>
 432 |           </div>
 433 |           <div class="rns-passport-row">
 434 |             <span class="rns-passport-key">Type</span>
 435 |             <span class="rns-passport-val">Digital Identity</span>
 436 |           </div>
 437 |           <div class="rns-passport-row">
 438 |             <span class="rns-passport-key">Jurisdiction</span>
 439 |             <span class="rns-passport-val">Pacific Island Nation</span>
 440 |           </div>
 441 |           <div class="rns-passport-row">
 442 |             <span class="rns-passport-key">BTC Friendly</span>
 443 |             <span class="rns-passport-val" style="color:var(--rns-green);">✓ YES</span>
 444 |           </div>
 445 |           <div class="rns-passport-row">
 446 |             <span class="rns-passport-key">Status</span>
 447 |             <span class="rns-passport-val" style="color:var(--rns-green);">Active Program</span>
 448 |           </div>
 449 |         </div>
 450 |         <div>
 451 |           <ul class="rns-what-points">
 452 |             <li class="rns-what-point">
 453 |               <span class="rns-point-icon">✓</span>
 454 |               <span><strong>Official digital identity</strong> issued by the Republic of Palau. Not crypto — real government-backed digital resident status recognized internationally.</span>
 455 |             </li>
 456 |             <li class="rns-what-point">
 457 |               <span class="rns-point-icon">✓</span>
 458 |               <span><strong>International banking access</strong> — the Palau digital ID enables financial services that may otherwise require traditional residency.</span>
 459 |             </li>
 460 |             <li class="rns-what-point">
 461 |               <span class="rns-point-icon">✓</span>
 462 |               <span><strong>Digital identity verification</strong> — establishes a verifiable, government-backed digital identity usable across multiple jurisdictions.</span>
 463 |             </li>
 464 |             <li class="rns-what-point">
 465 |               <span class="rns-point-icon">✓</span>
 466 |               <span><strong>Geographic diversification of identity</strong> — a second jurisdiction for identity reduces single-point-of-failure risk in your sovereignty stack.</span>
 467 |             </li>
 468 |           </ul>
 469 |         </div>
 470 |       </div>
 471 |     </div>
 472 |   </section>
 473 | 
 474 |   <!-- WHY BITCOINERS CARE -->
 475 |   <section class="rns-section">
 476 |     <div class="container">
 477 |       <div class="rns-section-kicker">The Bitcoin Angle</div>
 478 |       <h2 class="rns-section-title">Why Bitcoiners Care About This</h2>
 479 |       <div class="rns-cards">
 480 |         <div class="rns-card">
 481 |           <span class="rns-card-icon">🏝</span>
 482 |           <h3>Bitcoin-friendly jurisdiction</h3>
 483 |           <p>Palau is emerging as a progressive jurisdiction for digital assets and technology. Not a surveillance-first economy.</p>
 484 |         </div>
 485 |         <div class="rns-card">
 486 |           <span class="rns-card-icon">🔐</span>
 487 |           <h3>Privacy from surveillance finance</h3>
 488 |           <p>Establish an identity layer outside your home country's surveillance infrastructure. Your financial identity is your business.</p>
 489 |         </div>
 490 |         <div class="rns-card">
 491 |           <span class="rns-card-icon">📊</span>
 492 |           <h3>Tax optimization potential</h3>
 493 |           <p>Consult your legal advisor. Geographic diversification of identity can open planning opportunities unavailable to single-jurisdiction residents.</p>
 494 |         </div>
 495 |         <div class="rns-card">
 496 |           <span class="rns-card-icon">🌐</span>
 497 |           <h3>Geographic identity diversification</h3>
 498 |           <p>Don't put all your identity eggs in one jurisdiction's basket. Sovereignty means optionality — in money, in identity, in life.</p>
 499 |         </div>
 500 |       </div>
 501 |     </div>
 502 |   </section>
 503 | 
 504 |   <!-- EDITORIAL -->
 505 |   <section class="rns-section rns-what-bg">
 506 |     <div class="container">
 507 |       <div class="rns-section-kicker">Protocol Pulse Perspective</div>
 508 |       <h2 class="rns-section-title">Digital Sovereignty Starts with Identity</h2>
 509 |       <div class="rns-editorial">
 510 |         <div class="rns-editorial-byline">
 511 |           <div class="rns-editorial-avatar">PP</div>
 512 |           <div>
 513 |             <div class="rns-editorial-author">Protocol Pulse Editorial</div>
 514 |             <div class="rns-editorial-role">Intelligence for Transactors</div>
 515 |           </div>
 516 |         </div>
 517 |         <p>
 518 |           Bitcoin fixes money. It does not fix identity. The cypherpunk project has always
 519 |           been about more than sound money — it's about self-determination across every
 520 |           system that governments and corporations use to control and surveil you. Identity
 521 |           is one of the most overlooked attack surfaces in the sovereignty stack.
 522 |         </p>
 523 |         <p>
 524 |           When your digital identity is tied exclusively to one nation-state's infrastructure,
 525 |           you are one policy change, one sanctions regime, one banking shutdown away from
 526 |           being financially and digitally homeless. Palau digital residency isn't a silver
 527 |           bullet — it's an option. And in the sovereignty game, options are everything.
 528 |         </p>
 529 |         <p>
 530 |           We looked at RNS.ID and the Palau digital residency program carefully before
 531 |           adding it here. The program is real, the government backing is genuine, and
 532 |           for people who think seriously about jurisdictional risk, this is a legitimate
 533 |           tool worth knowing about. At $300 per referral, we earn a commission.
 534 |           We disclose this clearly and stand behind the product.
 535 |         </p>
 536 |         <div class="rns-affiliate-badge">
 537 |           ⚡ Affiliate Partnership — We earn $300 per referral.
 538 |           This is not legal or financial advice.
 539 |         </div>
 540 |       </div>
 541 | 
 542 |       <!-- Sovereignty Score -->
 543 |       <div class="rns-sov-score">
 544 |         <div class="rns-sov-title">Protocol Pulse Sovereignty Score — RNS.ID</div>
 545 |         <div class="rns-sov-rows">
 546 |           {% set scores = [
 547 |             ('Privacy', 5),
 548 |             ('BTC-Native Architecture', 3),
 549 |             ('Non-Custodial Structure', 5),
 550 |             ('Regulatory Compliance', 3),
 551 |             ('Transparency', 4)
 552 |           ] %}
 553 |           {% for label, score in scores %}
 554 |           <div class="rns-sov-row">
 555 |             <span class="rns-sov-label">{{ label }}</span>
 556 |             <div class="rns-sov-bars">
 557 |               {% for i in range(1, 6) %}
 558 |               <div class="rns-sov-bar {% if i <= score %}filled{% endif %}"></div>
 559 |               {% endfor %}
 560 |             </div>
 561 |             <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--rns-green);font-weight:700;">{{ score }}/5</span>
 562 |           </div>
 563 |           {% endfor %}
 564 |         </div>
 565 |       </div>
 566 |     </div>
 567 |   </section>
 568 | 
 569 |   <!-- FAQ -->
 570 |   <section class="rns-section">
 571 |     <div class="container">
 572 |       <div class="rns-section-kicker">Common Questions</div>
 573 |       <h2 class="rns-section-title">FAQ</h2>
 574 |       <div class="rns-faq" style="max-width:740px;">
 575 |         {% set faqs = [
 576 |           ("Is this a real government program?",
 577 |            "Yes. The Palau Digital Residency program is an official initiative of the Republic of Palau, a sovereign Pacific island nation. RNS.ID is the authorized platform for the application process."),
 578 |           ("Does it affect my current citizenship?",
 579 |            "No. Digital residency is not citizenship and does not affect your current citizenship status. It establishes a digital identity in Palau — it is not an immigration or naturalization product."),
 580 |           ("Can it help with banking access?",
 581 |            "Palau digital residency may open certain financial services that require a verified international identity. Specific benefits vary — consult RNS.ID and your legal advisor for details applicable to your situation."),
 582 |           ("Are there tax implications?",
 583 |            "Potentially, yes. Tax implications depend entirely on your home country's laws and your specific financial situation. We strongly recommend consulting a qualified international tax attorney before any decisions based on digital residency."),
 584 |           ("What's the application process?",
 585 |            "Applications are handled through RNS.ID's online platform. The process involves identity verification and payment. Visit our link for current application requirements and processing times."),
 586 |         ] %}
 587 |         {% for q, a in faqs %}
 588 |         <div class="rns-faq-item">
 589 |           <button class="rns-faq-q" onclick="toggleFaqRns(this)">{{ q }}</button>
 590 |           <div class="rns-faq-a">{{ a }}</div>
 591 |         </div>
 592 |         {% endfor %}
 593 |       </div>
 594 |     </div>
 595 |   </section>
 596 | 
 597 |   <!-- CTA FOOTER -->
 598 |   <section class="rns-cta-footer">
 599 |     <div class="container">
 600 |       <div class="rns-section-kicker" style="justify-content:center;">Take Action</div>
 601 |       <h2>Apply for Digital Residency</h2>
 602 |       <p>Start your sovereignty stack with a second jurisdiction. Digital freedom begins with digital identity.</p>
 603 |       <a href="/go/rns?ref=/digital-residency&v=footer"
 604 |          class="rns-cta-btn"
 605 |          data-partner="rns_id"
 606 |          onclick="trackAffClick('rns_id','footer')"
 607 |          style="font-size:1.1rem;padding:1rem 2.8rem;">
 608 |         Apply for Digital Residency →
 609 |       </a>
 610 |       <p class="rns-disclaimer">
 611 |         Protocol Pulse may earn compensation when you apply through our link.
 612 |         This is not legal or financial advice. Palau digital residency is not
 613 |         citizenship. Consult qualified legal counsel before making any decisions
 614 |         based on jurisdiction or tax planning.
 615 |       </p>
 616 |     </div>
 617 |   </section>
 618 | 
 619 | </div>
 620 | {% endblock %}
 621 | 
 622 | {% block extra_js %}
 623 | <script>
 624 | function toggleFaqRns(btn) {
 625 |     const item = btn.closest('.rns-faq-item');
 626 |     item.classList.toggle('open');
 627 |     btn.setAttribute('aria-expanded', item.classList.contains('open'));
 628 | }
 629 | 
 630 | function trackAffClick(partner, placement) {
 631 |     const payload = JSON.stringify({
 632 |         partner: partner,
 633 |         variant: 'B',
 634 |         referrer_page: window.location.pathname + '?placement=' + placement
 635 |     });
 636 |     if (navigator.sendBeacon) {
 637 |         navigator.sendBeacon('/api/affiliates/impression', new Blob([payload], {type:'application/json'}));
 638 |     }
 639 | }
 640 | 
 641 | document.querySelectorAll('.rns-faq-q').forEach(function(btn, i, all) {
 642 |     btn.setAttribute('aria-expanded', 'false');
 643 |     btn.addEventListener('keydown', function(e) {
 644 |         if (e.key === 'ArrowDown' && all[i+1]) { all[i+1].focus(); e.preventDefault(); }
 645 |         if (e.key === 'ArrowUp' && all[i-1]) { all[i-1].focus(); e.preventDefault(); }
 646 |     });
 647 | });
 648 | </script>
 649 | {% endblock %}
 650 | 
```

### File: services/affiliate_injector.py (544 lines)
```
   1 | """
   2 | services/affiliate_injector.py
   3 | Protocol Pulse P3 Affiliate Integration
   4 | AI-powered contextual CTA injection for Meanwhile + RNS.ID
   5 | 
   6 | Laws:
   7 |  - Contextual relevance only (no random spam)
   8 |  - A/B testing with Thompson Sampling MAB
   9 |  - IP never stored raw (SHA256+salt hash only)
  10 |  - Never on homepage/list pages — article detail only
  11 |  - Never both CTAs on same article
  12 |  - Never on breaking news articles
  13 | """
  14 | 
  15 | import hashlib
  16 | import logging
  17 | import math
  18 | import os
  19 | import random
  20 | import sqlite3
  21 | from datetime import datetime, date
  22 | from functools import lru_cache
  23 | from typing import Optional
  24 | 
  25 | import anthropic
  26 | 
  27 | logger = logging.getLogger(__name__)
  28 | 
  29 | # ────────────────────────────────────────────────────────────
  30 | # Partner config
  31 | # ────────────────────────────────────────────────────────────
  32 | PARTNER_CONFIG = {
  33 |     "meanwhile": {
  34 |         "name": "Meanwhile Bitcoin Life Insurance",
  35 |         "redirect_url": "https://www.meanwhile.life/?ref=KKM73K",
  36 |         "referral_code": "KKM73K",
  37 |         "landing_page": "/bitcoin-life-insurance",
  38 |         "redirect_path": "/go/meanwhile",
  39 |         "triggers": {"wealth", "insurance", "sovereignty", "estate-planning",
  40 |                      "inheritance", "generational", "family", "legacy", "finance",
  41 |                      "savings", "retirement", "protection", "estate", "bitcoin-insurance"},
  42 |         "exclude_categories": {"breaking-news", "breaking"},
  43 |         "estimated_commission": 150.0,
  44 |         "sovereignty_score": {
  45 |             "privacy": 4,
  46 |             "btc_native": 5,
  47 |             "non_custodial": 3,
  48 |             "regulatory": 4,
  49 |             "transparency": 4,
  50 |         },
  51 |     },
  52 |     "rns_id": {
  53 |         "name": "RNS.ID Palau Digital Residency",
  54 |         "redirect_url": "https://rns.id/?ref=protocolpulse",
  55 |         "referral_code": "protocolpulse",
  56 |         "landing_page": "/digital-residency",
  57 |         "redirect_path": "/go/rns",
  58 |         "triggers": {"regulation", "privacy", "sovereignty", "residency", "global",
  59 |                      "identity", "kyc", "censorship", "surveillance", "jurisdiction",
  60 |                      "offshore", "banking", "digital-id", "freedom-tech", "cypherpunk"},
  61 |         "exclude_categories": {"breaking-news", "breaking"},
  62 |         "estimated_commission": 300.0,
  63 |         "sovereignty_score": {
  64 |             "privacy": 5,
  65 |             "btc_native": 3,
  66 |             "non_custodial": 5,
  67 |             "regulatory": 3,
  68 |             "transparency": 4,
  69 |         },
  70 |     },
  71 | }
  72 | 
  73 | # Category tags that map to partner triggers
  74 | MEANWHILE_TAGS = frozenset(PARTNER_CONFIG["meanwhile"]["triggers"])
  75 | RNS_TAGS = frozenset(PARTNER_CONFIG["rns_id"]["triggers"])
  76 | 
  77 | 
  78 | # ────────────────────────────────────────────────────────────
  79 | # Claude Haiku classification
  80 | # ────────────────────────────────────────────────────────────
  81 | @lru_cache(maxsize=512)
  82 | def _classify_article(article_id: int, content_snippet: str) -> dict:
  83 |     """
  84 |     Use Claude Haiku to classify article themes.
  85 |     Returns {meanwhile: bool, rns_id: bool, themes: list[str]}.
  86 |     Cached per article_id so we only call API once per article.
  87 |     """
  88 |     try:
  89 |         client = anthropic.Anthropic(
  90 |             api_key=os.environ.get("ANTHROPIC_API_KEY"),
  91 |         )
  92 | 
  93 |         system_prompt = (
  94 |             "You are a content classifier for a Bitcoin media publication. "
  95 |             "Classify the article excerpt into relevant themes. "
  96 |             "Respond ONLY with a JSON object. No explanations.\n"
  97 |             "Format: {\"themes\": [\"list of theme keywords\"], "
  98 |             "\"meanwhile_relevant\": true/false, "
  99 |             "\"rns_relevant\": true/false}\n\n"
 100 |             "meanwhile_relevant = true if article discusses: "
 101 |             "wealth, estate planning, insurance, generational wealth, "
 102 |             "inheritance, Bitcoin savings, family finance, legacy planning, "
 103 |             "life insurance, retirement, financial sovereignty.\n\n"
 104 |             "rns_relevant = true if article discusses: "
 105 |             "regulation, surveillance, KYC, identity, digital residency, "
 106 |             "privacy, sovereignty, offshore banking, censorship resistance, "
 107 |             "jurisdiction shopping, freedom tech, cypherpunk topics.\n\n"
 108 |             "Breaking news / price action articles = both false.\n"
 109 |             "Never set both to true for the same article."
 110 |         )
 111 | 
 112 |         resp = client.messages.create(
 113 |             model="claude-haiku-4-5-20251001",
 114 |             max_tokens=256,
 115 |             system=system_prompt,
 116 |             messages=[{"role": "user", "content": content_snippet[:1500]}],
 117 |             timeout=10,
 118 |         )
 119 | 
 120 |         import json as _json
 121 |         raw = resp.content[0].text.strip()
 122 |         # Strip potential markdown fences
 123 |         if raw.startswith("```"):
 124 |             raw = raw.split("```")[1]
 125 |             if raw.startswith("json"):
 126 |                 raw = raw[4:]
 127 |         result = _json.loads(raw)
 128 |         return {
 129 |             "meanwhile": bool(result.get("meanwhile_relevant", False)),
 130 |             "rns_id": bool(result.get("rns_relevant", False)),
 131 |             "themes": result.get("themes", []),
 132 |         }
 133 |     except Exception as exc:
 134 |         logger.warning("affiliate_injector classify error: %s", exc)
 135 |         # Fallback: keyword-based classification
 136 |         content_lower = content_snippet.lower()
 137 |         meanwhile = any(kw in content_lower for kw in
 138 |                         ["insurance", "estate", "inheritance", "legacy", "generational",
 139 |                          "life insurance", "protection", "wealth", "retirement"])
 140 |         rns = any(kw in content_lower for kw in
 141 |                   ["regulation", "surveillance", "kyc", "identity", "residency",
 142 |                    "privacy", "sovereignty", "censorship", "offshore"])
 143 |         return {"meanwhile": meanwhile and not rns, "rns_id": rns and not meanwhile, "themes": []}
 144 | 
 145 | 
 146 | # ────────────────────────────────────────────────────────────
 147 | # Thompson Sampling MAB
 148 | # ────────────────────────────────────────────────────────────
 149 | def _get_mab_weights(partner: str) -> tuple[float, float]:
 150 |     """
 151 |     Read MAB state from DB. Returns (weight_A, weight_B) as probabilities summing to 1.
 152 |     Falls back to 50/50 if no data.
 153 |     Uses Thompson Sampling: sample from Beta(alpha, beta) for each arm, pick higher.
 154 |     At low data counts (<100 total clicks), returns 0.5/0.5.
 155 |     """
 156 |     try:
 157 |         from app import db
 158 |         import sqlalchemy
 159 |         result = db.session.execute(
 160 |             sqlalchemy.text(
 161 |                 "SELECT variant, impressions, clicks FROM p3_affiliate_ab_results "
 162 |                 "WHERE partner = :partner ORDER BY variant"
 163 |             ),
 164 |             {"partner": partner},
 165 |         ).fetchall()
 166 | 
 167 |         rows = {r[0]: (r[1], r[2]) for r in result}
 168 |         a_impr, a_clicks = rows.get("A", (0, 0))
 169 |         b_impr, b_clicks = rows.get("B", (0, 0))
 170 | 
 171 |         total = a_impr + b_impr
 172 |         if total < 100:
 173 |             return 0.5, 0.5
 174 | 
 175 |         # Thompson Sampling: sample from Beta distribution
 176 |         # alpha = clicks + 1, beta = (impressions - clicks) + 1
 177 |         a_alpha = a_clicks + 1
 178 |         a_beta = max(a_impr - a_clicks, 0) + 1
 179 |         b_alpha = b_clicks + 1
 180 |         b_beta = max(b_impr - b_clicks, 0) + 1
 181 | 
 182 |         # Monte Carlo Thompson Sampling approximation (no scipy)
 183 |         # Use closed-form: expected value of Beta = alpha/(alpha+beta)
 184 |         # For allocation, sample 1000 times and count wins
 185 |         wins_a = 0
 186 |         for _ in range(200):
 187 |             sample_a = _beta_sample(a_alpha, a_beta)
 188 |             sample_b = _beta_sample(b_alpha, b_beta)
 189 |             if sample_a > sample_b:
 190 |                 wins_a += 1
 191 | 
 192 |         weight_a = wins_a / 200
 193 |         weight_b = 1.0 - weight_a
 194 |         # Clip to prevent 0% allocation (exploration)
 195 |         weight_a = max(0.05, min(0.95, weight_a))
 196 |         weight_b = 1.0 - weight_a
 197 |         return weight_a, weight_b
 198 | 
 199 |     except Exception as exc:
 200 |         logger.debug("MAB weight lookup failed: %s", exc)
 201 |         return 0.5, 0.5
 202 | 
 203 | 
 204 | def _beta_sample(alpha: float, beta: float) -> float:
 205 |     """
 206 |     Sample from Beta(alpha, beta) distribution using Johnk's method.
 207 |     Pure Python, no numpy/scipy.
 208 |     """
 209 |     try:
 210 |         return random.betavariate(alpha, beta)
 211 |     except Exception:
 212 |         return alpha / (alpha + beta)
 213 | 
 214 | 
 215 | def _get_ab_variant(partner: str, user_hash: str) -> str:
 216 |     """
 217 |     Determine A/B variant for a user.
 218 |     Uses deterministic hash, weighted by current MAB allocation.
 219 |     Consistent: same user+date → same variant, but allocation shifts over time.
 220 |     """
 221 |     weight_a, _ = _get_mab_weights(partner)
 222 |     # Deterministic value 0.0 - 1.0 from hash
 223 |     hash_val = int(hashlib.sha256(f"{user_hash}:{partner}".encode()).hexdigest()[:8], 16)
 224 |     normalized = hash_val / 0xFFFFFFFF
 225 |     return "A" if normalized < weight_a else "B"
 226 | 
 227 | 
 228 | # ────────────────────────────────────────────────────────────
 229 | # CTA HTML generation
 230 | # ────────────────────────────────────────────────────────────
 231 | def _render_cta(partner: str, variant: str) -> str:
 232 |     """Generate CTA HTML for a given partner and variant."""
 233 |     cfg = PARTNER_CONFIG[partner]
 234 |     path = cfg["redirect_path"]
 235 |     landing = cfg["landing_page"]
 236 | 
 237 |     if partner == "meanwhile":
 238 |         if variant == "A":
 239 |             return (
 240 |                 f'<span class="affiliate-inline" data-partner="meanwhile" data-variant="A">'
 241 |                 f'Tools like <a href="{path}" class="aff-link-inline" '
 242 |                 f'data-partner="meanwhile">Meanwhile</a> let Bitcoiners protect '
 243 |                 f'generational wealth with BTC-denominated life insurance.</span>'
 244 |             )
 245 |         else:  # Variant B — card
 246 |             return f"""<div class="affiliate-card" data-partner="meanwhile" data-variant="B" role="complementary" aria-label="Affiliate: Meanwhile Bitcoin Insurance">
 247 |   <div class="aff-card-inner">
 248 |     <div class="aff-card-badge">AFFILIATE PARTNERSHIP</div>
 249 |     <div class="aff-card-header">
 250 |       <span class="aff-card-icon">🛡</span>
 251 |       <div class="aff-card-title-wrap">
 252 |         <span class="aff-card-title">Meanwhile</span>
 253 |         <span class="aff-card-subtitle">Bitcoin Life Insurance</span>
 254 |       </div>
 255 |     </div>
 256 |     <p class="aff-card-pitch">Death benefit in BTC — your family inherits sovereignty, not a fiat check. <strong>Self-sovereign estate planning.</strong></p>
 257 |     <a href="{path}" class="aff-card-cta" data-partner="meanwhile" aria-label="Learn more about Meanwhile Bitcoin Life Insurance">Learn More →</a>
 258 |   </div>
 259 | </div>"""
 260 | 
 261 |     else:  # rns_id
 262 |         if variant == "A":
 263 |             return (
 264 |                 f'<span class="affiliate-inline" data-partner="rns_id" data-variant="A">'
 265 |                 f'Establishing a <a href="{path}" class="aff-link-inline" '
 266 |                 f'data-partner="rns_id">Palau digital residency</a> via RNS.ID offers '
 267 |                 f'a government-issued digital identity outside traditional financial '
 268 |                 f'surveillance systems.</span>'
 269 |             )
 270 |         else:  # Variant B — card
 271 |             return f"""<div class="affiliate-card" data-partner="rns_id" data-variant="B" role="complementary" aria-label="Affiliate: RNS.ID Digital Residency">
 272 |   <div class="aff-card-inner">
 273 |     <div class="aff-card-badge">AFFILIATE PARTNERSHIP</div>
 274 |     <div class="aff-card-header">
 275 |       <span class="aff-card-icon">🌐</span>
 276 |       <div class="aff-card-title-wrap">
 277 |         <span class="aff-card-title">RNS.ID</span>
 278 |         <span class="aff-card-subtitle">Palau Digital Residency</span>
 279 |       </div>
 280 |     </div>
 281 |     <p class="aff-card-pitch">A government-issued digital ID outside the surveillance state. <strong>Digital sovereignty starts with identity.</strong></p>
 282 |     <a href="{path}" class="aff-card-cta aff-cta-green" data-partner="rns_id" aria-label="Apply for Palau Digital Residency">Apply Now →</a>
 283 |   </div>
 284 | </div>"""
 285 | 
 286 | 
 287 | # ────────────────────────────────────────────────────────────
 288 | # Main injection function
 289 | # ────────────────────────────────────────────────────────────
 290 | def inject_affiliate_cta(
 291 |     article_id: int,
 292 |     article_content: str,
 293 |     article_category: str,
 294 |     article_tags: str,
 295 |     client_ip: str,
 296 | ) -> Optional[dict]:
 297 |     """
 298 |     Determine whether to inject an affiliate CTA for this article.
 299 | 
 300 |     Returns dict with {partner, variant, cta_html, partner_cfg} or None.
 301 |     Never returns CTA for breaking news or if category is excluded.
 302 |     Never returns both partners on same article.
 303 |     """
 304 |     try:
 305 |         # Check for breaking news / exclusion
 306 |         cat_lower = (article_category or "").lower()
 307 |         if "breaking" in cat_lower:
 308 |             return None
 309 | 
 310 |         # Build content snippet for classification
 311 |         content_snippet = (article_content or "")[:2000]
 312 |         tags_lower = (article_tags or "").lower()
 313 | 
 314 |         # AI classification (cached by article_id)
 315 |         classification = _classify_article(article_id, content_snippet)
 316 | 
 317 |         meanwhile_ok = classification.get("meanwhile", False)
 318 |         rns_ok = classification.get("rns_id", False)
 319 | 
 320 |         # Also check tags for fast-path if AI disabled
 321 |         if not meanwhile_ok and not rns_ok:
 322 |             meanwhile_ok = any(t in tags_lower for t in MEANWHILE_TAGS)
 323 |             rns_ok = any(t in tags_lower for t in RNS_TAGS)
 324 | 
 325 |         # Never show both — pick one (meanwhile wins ties)
 326 |         if meanwhile_ok and rns_ok:
 327 |             rns_ok = False  # meanwhile takes priority
 328 | 
 329 |         if not meanwhile_ok and not rns_ok:
 330 |             return None
 331 | 
 332 |         partner = "meanwhile" if meanwhile_ok else "rns_id"
 333 | 
 334 |         # Generate user hash (privacy-first: never store raw IP)
 335 |         salt = os.environ.get("TRACKING_SALT", "pp-affiliate-default-salt-2026")
 336 |         today = date.today().isoformat()
 337 |         user_hash = hashlib.sha256(f"{client_ip}:{today}:{salt}".encode()).hexdigest()
 338 | 
 339 |         # MAB variant assignment
 340 |         variant = _get_ab_variant(partner, user_hash)
 341 | 
 342 |         # Render CTA HTML
 343 |         cta_html = _render_cta(partner, variant)
 344 | 
 345 |         return {
 346 |             "partner": partner,
 347 |             "variant": variant,
 348 |             "cta_html": cta_html,
 349 |             "user_hash": user_hash,
 350 |             "partner_cfg": PARTNER_CONFIG[partner],
 351 |         }
 352 | 
 353 |     except Exception as exc:
 354 |         logger.warning("inject_affiliate_cta error article_id=%s: %s", article_id, exc)
 355 |         return None
 356 | 
 357 | 
 358 | # ────────────────────────────────────────────────────────────
 359 | # DB helpers
 360 | # ────────────────────────────────────────────────────────────
 361 | def track_click(partner: str, referrer_page: str, ab_variant: str,
 362 |                 user_hash: str, user_agent: str) -> bool:
 363 |     """Record a click in p3_affiliate_clicks. Returns True on success."""
 364 |     try:
 365 |         from app import db
 366 |         import sqlalchemy
 367 |         ua_hash = hashlib.sha256((user_agent or "").encode()).hexdigest()
 368 |         db.session.execute(
 369 |             sqlalchemy.text(
 370 |                 "INSERT INTO p3_affiliate_clicks "
 371 |                 "(partner, referrer_page, ab_variant, converted, user_hash, "
 372 |                 "user_agent_hash, clicked_at) "
 373 |                 "VALUES (:partner, :ref, :variant, 0, :uhash, :uahash, :now)"
 374 |             ),
 375 |             {
 376 |                 "partner": partner,
 377 |                 "ref": referrer_page or "",
 378 |                 "variant": ab_variant or "A",
 379 |                 "uhash": user_hash,
 380 |                 "uahash": ua_hash,
 381 |                 "now": datetime.utcnow().isoformat(),
 382 |             },
 383 |         )
 384 |         db.session.commit()
 385 | 
 386 |         # Increment AB results
 387 |         _increment_ab_clicks(partner, ab_variant)
 388 |         return True
 389 |     except Exception as exc:
 390 |         logger.error("track_click failed: %s", exc)
 391 |         try:
 392 |             from app import db as _db
 393 |             _db.session.rollback()
 394 |         except Exception:
 395 |             pass
 396 |         return False
 397 | 
 398 | 
 399 | def track_impression(partner: str, referrer_page: str, ab_variant: str,
 400 |                      user_hash: str) -> bool:
 401 |     """Record an impression in p3_affiliate_ab_results."""
 402 |     try:
 403 |         _increment_ab_impressions(partner, ab_variant)
 404 |         return True
 405 |     except Exception as exc:
 406 |         logger.debug("track_impression failed: %s", exc)
 407 |         return False
 408 | 
 409 | 
 410 | def _increment_ab_impressions(partner: str, variant: str):
 411 |     """Atomically increment impression count for a variant."""
 412 |     from app import db
 413 |     import sqlalchemy
 414 |     # Upsert pattern
 415 |     existing = db.session.execute(
 416 |         sqlalchemy.text(
 417 |             "SELECT id FROM p3_affiliate_ab_results "
 418 |             "WHERE partner = :partner AND variant = :variant"
 419 |         ),
 420 |         {"partner": partner, "variant": variant},
 421 |     ).fetchone()
 422 | 
 423 |     if existing:
 424 |         db.session.execute(
 425 |             sqlalchemy.text(
 426 |                 "UPDATE p3_affiliate_ab_results SET impressions = impressions + 1, "
 427 |                 "calculated_at = :now WHERE partner = :partner AND variant = :variant"
 428 |             ),
 429 |             {"now": datetime.utcnow().isoformat(), "partner": partner, "variant": variant},
 430 |         )
 431 |     else:
 432 |         db.session.execute(
 433 |             sqlalchemy.text(
 434 |                 "INSERT INTO p3_affiliate_ab_results "
 435 |                 "(partner, variant, impressions, clicks, calculated_at) "
 436 |                 "VALUES (:partner, :variant, 1, 0, :now)"
 437 |             ),
 438 |             {"partner": partner, "variant": variant, "now": datetime.utcnow().isoformat()},
 439 |         )
 440 |     db.session.commit()
 441 | 
 442 | 
 443 | def _increment_ab_clicks(partner: str, variant: str):
 444 |     """Atomically increment click count for a variant."""
 445 |     from app import db
 446 |     import sqlalchemy
 447 |     existing = db.session.execute(
 448 |         sqlalchemy.text(
 449 |             "SELECT id FROM p3_affiliate_ab_results "
 450 |             "WHERE partner = :partner AND variant = :variant"
 451 |         ),
 452 |         {"partner": partner, "variant": variant},
 453 |     ).fetchone()
 454 | 
 455 |     if existing:
 456 |         db.session.execute(
 457 |             sqlalchemy.text(
 458 |                 "UPDATE p3_affiliate_ab_results SET clicks = clicks + 1, "
 459 |                 "calculated_at = :now WHERE partner = :partner AND variant = :variant"
 460 |             ),
 461 |             {"now": datetime.utcnow().isoformat(), "partner": partner, "variant": variant},
 462 |         )
 463 |     else:
 464 |         db.session.execute(
 465 |             sqlalchemy.text(
 466 |                 "INSERT INTO p3_affiliate_ab_results "
 467 |                 "(partner, variant, impressions, clicks, calculated_at) "
 468 |                 "VALUES (:partner, :variant, 1, 1, :now)"
 469 |             ),
 470 |             {"partner": partner, "variant": variant, "now": datetime.utcnow().isoformat()},
 471 |         )
 472 |     db.session.commit()
 473 | 
 474 | 
 475 | # ────────────────────────────────────────────────────────────
 476 | # Statistical significance (no scipy)
 477 | # ────────────────────────────────────────────────────────────
 478 | def compute_ab_stats(partner: str) -> dict:
 479 |     """
 480 |     Compute A/B test statistics for a partner.
 481 |     Returns significance, winning variant, confidence level.
 482 |     """
 483 |     try:
 484 |         from app import db
 485 |         import sqlalchemy
 486 |         rows = db.session.execute(
 487 |             sqlalchemy.text(
 488 |                 "SELECT variant, impressions, clicks FROM p3_affiliate_ab_results "
 489 |                 "WHERE partner = :partner"
 490 |             ),
 491 |             {"partner": partner},
 492 |         ).fetchall()
 493 | 
 494 |         data = {r[0]: {"impressions": r[1], "clicks": r[2]} for r in rows}
 495 |         a = data.get("A", {"impressions": 0, "clicks": 0})
 496 |         b = data.get("B", {"impressions": 0, "clicks": 0})
 497 | 
 498 |         n_a = max(a["impressions"], 1)
 499 |         n_b = max(b["impressions"], 1)
 500 |         c_a = a["clicks"]
 501 |         c_b = b["clicks"]
 502 | 
 503 |         p_a = c_a / n_a
 504 |         p_b = c_b / n_b
 505 | 
 506 |         total_c = c_a + c_b
 507 |         total_n = n_a + n_b
 508 |         p_pool = total_c / total_n if total_n > 0 else 0.5
 509 | 
 510 |         # Two-proportion z-test
 511 |         se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
 512 |         z = (p_a - p_b) / se if se > 0 else 0
 513 | 
 514 |         # Approximate p-value using erf
 515 |         p_val = 1.0 - math.erf(abs(z) / math.sqrt(2))
 516 | 
 517 |         winning = "A" if p_a > p_b else "B"
 518 |         confident = p_val < 0.05 and min(n_a, n_b) >= 100
 519 | 
 520 |         return {
 521 |             "variant_a": {"impressions": n_a, "clicks": c_a, "ctr": round(p_a * 100, 2)},
 522 |             "variant_b": {"impressions": n_b, "clicks": c_b, "ctr": round(p_b * 100, 2)},
 523 |             "z_score": round(z, 3),
 524 |             "p_value": round(p_val, 4),
 525 |             "significant": confident,
 526 |             "winning_variant": winning if confident else None,
 527 |             "confidence_pct": round((1 - p_val) * 100, 1),
 528 |             "needs_more_data": min(n_a, n_b) < 100,
 529 |         }
 530 |     except Exception as exc:
 531 |         logger.warning("compute_ab_stats error: %s", exc)
 532 |         return {"error": str(exc)}
 533 | 
 534 | 
 535 | def get_partner_config() -> dict:
 536 |     """Return full partner config (public fields only)."""
 537 |     return {k: {
 538 |         "name": v["name"],
 539 |         "landing_page": v["landing_page"],
 540 |         "redirect_path": v["redirect_path"],
 541 |         "estimated_commission": v["estimated_commission"],
 542 |         "sovereignty_score": v["sovereignty_score"],
 543 |     } for k, v in PARTNER_CONFIG.items()}
 544 | 
```

### File: templates/media_unified.html (809 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Media Hub — Protocol Pulse Intelligence{% endblock %}
   3 | {% block meta_description %}Live Bitcoin intelligence terminal. Nostr feeds, on-chain data, sentiment analysis, and original podcast content.{% endblock %}
   4 | 
   5 | {% block head %}
   6 | <link rel="preconnect" href="https://fonts.googleapis.com">
   7 | <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   8 | <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Instrument+Serif&family=Geist+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
   9 | <link rel="stylesheet" href="/static/css/media_unified_v5.css">
  10 | {% endblock %}
  11 | 
  12 | {% block body_class %}mu-page{% endblock %}
  13 | 
  14 | {% block content %}
  15 | 
  16 | <!-- ════════════════════════════════════════════════════
  17 |      TELEMETRY RIBBON (sticky below nav)
  18 |      ════════════════════════════════════════════════════ -->
  19 | <div class="mu-telemetry" id="mu-telemetry">
  20 |   <div class="mu-telemetry-inner">
  21 |     <!-- Fee Rate -->
  22 |     <div class="mu-telem-metric">
  23 |       <span class="mu-telem-value" id="telem-fees" data-metric="fees">--</span>
  24 |       <canvas class="mu-sparkline" id="spark-fees" width="40" height="12"></canvas>
  25 |       <span class="mu-telem-label">sat/vB</span>
  26 |     </div>
  27 | 
  28 |     <div class="mu-telem-sep"></div>
  29 | 
  30 |     <!-- Mempool -->
  31 |     <div class="mu-telem-metric">
  32 |       <span class="mu-telem-value" id="telem-mempool" data-metric="mempool">--</span>
  33 |       <canvas class="mu-sparkline" id="spark-mempool" width="40" height="12"></canvas>
  34 |       <span class="mu-telem-label">MB</span>
  35 |     </div>
  36 | 
  37 |     <div class="mu-telem-sep"></div>
  38 | 
  39 |     <!-- Hashrate -->
  40 |     <div class="mu-telem-metric">
  41 |       <span class="mu-telem-value" id="telem-hashrate" data-metric="hashrate">--</span>
  42 |       <canvas class="mu-sparkline" id="spark-hashrate" width="40" height="12"></canvas>
  43 |       <span class="mu-telem-label">EH/s</span>
  44 |     </div>
  45 | 
  46 |     <div class="mu-telem-sep"></div>
  47 | 
  48 |     <!-- Block Height -->
  49 |     <div class="mu-telem-metric">
  50 |       <span class="mu-telem-value mu-telem-btc" id="telem-block" data-metric="block">--</span>
  51 |       <span class="mu-telem-label">BLOCK</span>
  52 |     </div>
  53 | 
  54 |     <div class="mu-telem-sep"></div>
  55 | 
  56 |     <!-- Signal Strength -->
  57 |     <div class="mu-telem-metric mu-telem-signal">
  58 |       <span class="mu-telem-label">SIGNAL</span>
  59 |       <span class="mu-telem-value" id="telem-signal">0</span>
  60 |       <div class="mu-signal-bar">
  61 |         <div class="mu-signal-fill" id="signal-fill"></div>
  62 |       </div>
  63 |     </div>
  64 | 
  65 |     <div class="mu-telem-sep"></div>
  66 | 
  67 |     <!-- X Spaces -->
  68 |     <div class="mu-telem-metric" title="X Spaces Sentiment">
  69 |       <span class="mu-telem-label">X SPACES</span>
  70 |       <span class="mu-telem-value" id="telem-xs-score" style="min-width:24px;">--</span>
  71 |       <span class="mu-telem-label" id="telem-xs-label" style="font-size:0.55rem;"></span>
  72 |     </div>
  73 | 
  74 |     <!-- Sentiment Track -->
  75 |     <div class="mu-sentiment-track-wrap">
  76 |       <span class="mu-sentiment-label-l">FEAR</span>
  77 |       <div class="mu-sentiment-track" id="sentiment-track">
  78 |         <div class="mu-sentiment-dot" id="sentiment-dot"></div>
  79 |       </div>
  80 |       <span class="mu-sentiment-label-r">GREED</span>
  81 |       <span class="mu-sentiment-num" id="sentiment-num">--</span>
  82 |     </div>
  83 |     <div class="mu-sentiment-why" id="sentiment-why"></div>
  84 | 
  85 |     <!-- Health Dots -->
  86 |     <div class="mu-health">
  87 |       <div class="mu-health-dot loading" id="health-nostr" title="Nostr"></div>
  88 |       <div class="mu-health-dot loading" id="health-telemetry" title="Telemetry"></div>
  89 |       <div class="mu-health-dot loading" id="health-sentiment" title="Sentiment"></div>
  90 |       <div class="mu-health-dot loading" id="health-xspaces" title="X Spaces"></div>
  91 |     </div>
  92 | 
  93 |     <!-- Cmd+K -->
  94 |     <div class="mu-cmdk-hint" id="cmd-k-hint">&#x2318;K</div>
  95 |   </div>
  96 | 
  97 |   <!-- Thermal border -->
  98 |   <div class="mu-thermal-border" id="thermal-border"></div>
  99 | </div>
 100 | 
 101 | <!-- ════════════════════════════════════════════════════
 102 |      HERO: Featured Media + Delta Card
 103 |      ════════════════════════════════════════════════════ -->
 104 | <section class="mu-hero">
 105 |   <!-- Featured — text IS the hero -->
 106 |   <div class="mu-featured" id="mu-featured">
 107 |     <div class="mu-featured-text" id="hero-text">
 108 |       <span class="mu-latest-label">LATEST</span>
 109 |       {% if latest_episodes and latest_episodes|length > 0 %}
 110 |         {% set ep = latest_episodes[0] %}
 111 |         <h1 class="mu-hero-title">{{ ep.title }}</h1>
 112 |         <div class="mu-hero-meta">
 113 |           <span>EP {{ loop.index if loop is defined else podcast_count }}</span>
 114 |           <span class="mu-hero-dot">&middot;</span>
 115 |           <span>PROTOCOL PULSE</span>
 116 |           <span class="mu-hero-dot">&middot;</span>
 117 |           <span>{{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}</span>
 118 |         </div>
 119 |         <button class="mu-play-btn" id="hero-play"
 120 |                 data-vid="{{ ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' }}">
 121 |           <span class="mu-play-icon">&#9654;</span>
 122 |           <span>PLAY</span>
 123 |         </button>
 124 |       {% else %}
 125 |         <h1 class="mu-hero-title">Protocol Pulse</h1>
 126 |         <div class="mu-hero-meta">
 127 |           <span>{{ podcast_count }} episodes</span>
 128 |         </div>
 129 |       {% endif %}
 130 |     </div>
 131 |     <!-- YouTube embed appears here on play click -->
 132 |     <div class="mu-featured-embed" id="hero-embed"></div>
 133 |   </div>
 134 | 
 135 |   <!-- Since You Were Gone -->
 136 |   <div class="mu-delta" id="mu-delta">
 137 |     <div class="mu-delta-count" id="delta-count">...</div>
 138 |     <div class="mu-delta-label" id="delta-label">Loading intelligence...</div>
 139 |     <div class="mu-delta-items" id="delta-items"></div>
 140 |     <button class="mu-delta-showme" id="delta-showme">&darr; SHOW ME</button>
 141 |   </div>
 142 | </section>
 143 | 
 144 | <!-- ════════════════════════════════════════════════════
 145 |      SIGNAL DASHBOARD: 2 Columns
 146 |      ════════════════════════════════════════════════════ -->
 147 | <section class="mu-signals" id="mu-signals">
 148 |   <!-- Left: Nostr + X Live -->
 149 |   <div class="mu-col">
 150 |     <div class="mu-col-header">
 151 |       <span class="mu-col-title">NOSTR + X LIVE</span>
 152 |       <span class="mu-col-source"><span class="mu-health-dot" id="health-nostr-col"></span></span>
 153 |     </div>
 154 |     <!-- D4: Relay Status Bar -->
 155 |     <div class="mu-relay-status-bar" id="relay-status-bar">
 156 |       <div class="mu-relay-item" data-relay="relay.damus.io">
 157 |         <div class="mu-relay-dot" style="background:#555"></div>
 158 |         <span class="mu-relay-name">damus</span>
 159 |         <span class="mu-relay-status">OFFLINE</span>
 160 |         <span class="mu-relay-count">0 notes</span>
 161 |       </div>
 162 |       <div class="mu-relay-item" data-relay="nos.lol">
 163 |         <div class="mu-relay-dot" style="background:#555"></div>
 164 |         <span class="mu-relay-name">nos.lol</span>
 165 |         <span class="mu-relay-status">OFFLINE</span>
 166 |         <span class="mu-relay-count">0 notes</span>
 167 |       </div>
 168 |       <div class="mu-relay-item" data-relay="relay.nostr.band">
 169 |         <div class="mu-relay-dot" style="background:#555"></div>
 170 |         <span class="mu-relay-name">nostr.band</span>
 171 |         <span class="mu-relay-status">OFFLINE</span>
 172 |         <span class="mu-relay-count">0 notes</span>
 173 |       </div>
 174 |     </div>
 175 |     <div class="mu-col-feed" id="nostr-feed"></div>
 176 |     <div class="mu-col-count" id="nostr-count">0 notes</div>
 177 |   </div>
 178 | 
 179 |   <div class="mu-col-divider"></div>
 180 | 
 181 |   <!-- Right: Verified Highlights -->
 182 |   <div class="mu-col">
 183 |     <div class="mu-col-header">
 184 |       <span class="mu-col-title">VERIFIED HIGHLIGHTS</span>
 185 |       <span class="mu-col-source">partner channels <span class="mu-health-dot connected" id="health-highlights-col"></span></span>
 186 |     </div>
 187 |     <div class="mu-col-feed" id="highlights-feed">
 188 |       {% if ssr_highlights %}
 189 |         {% for h in ssr_highlights %}
 190 |         <div class="mu-highlight-item">
 191 |           <div class="mu-highlight-quote">&ldquo;{{ h.excerpt[:180] }}&rdquo;</div>
 192 |           <div class="mu-highlight-source">&mdash; {{ h.source }}{% if h.direction == 'bullish' %} <span style="color:#22c55e">BULLISH</span>{% elif h.direction == 'bearish' %} <span style="color:#dc2626">BEARISH</span>{% endif %}</div>
 193 |         </div>
 194 |         {% endfor %}
 195 |       {% endif %}
 196 |     </div>
 197 |   </div>
 198 | </section>
 199 | 
 200 | <!-- ════════════════════════════════════════════════════
 201 |      SIGNAL STRENGTH GAUGE (Phase 2)
 202 |      ════════════════════════════════════════════════════ -->
 203 | <section class="mu-section mu-signal-section" id="mu-signal-section">
 204 |   <div class="mu-section-head">
 205 |     <h2 class="mu-section-title">SIGNAL STRENGTH</h2>
 206 |     <span class="mu-section-sub">Composite intelligence score — live</span>
 207 |   </div>
 208 |   <div class="mu-signal-gauge-wrap">
 209 |     <div id="signal-strength-gauge">
 210 |       <div class="mu-gauge-ring" style="--score:50%;--color:#E67E22">
 211 |         <div class="mu-gauge-inner">
 212 |           <div class="mu-gauge-score">--</div>
 213 |           <div class="mu-gauge-label">SIGNAL</div>
 214 |           <div class="mu-gauge-level">LOADING</div>
 215 |         </div>
 216 |       </div>
 217 |     </div>
 218 |     <div class="mu-signal-breakdown" id="signal-breakdown">
 219 |       <div class="mu-sig-row">
 220 |         <span class="mu-sig-key">SENTIMENT</span>
 221 |         <span class="mu-sig-val" id="sig-sentiment">--</span>
 222 |         <span class="mu-sig-weight">70%</span>
 223 |       </div>
 224 |       <div class="mu-sig-row">
 225 |         <span class="mu-sig-key">X SPACES</span>
 226 |         <span class="mu-sig-val" id="sig-spaces">--</span>
 227 |         <span class="mu-sig-weight">30%</span>
 228 |       </div>
 229 |       <div class="mu-sig-row mu-sig-total">
 230 |         <span class="mu-sig-key">COMPOSITE</span>
 231 |         <span class="mu-sig-val" id="sig-composite">--</span>
 232 |         <span class="mu-sig-weight">&nbsp;</span>
 233 |       </div>
 234 |     </div>
 235 |   </div>
 236 | </section>
 237 | 
 238 | <!-- ════════════════════════════════════════════════════
 239 |      REDDIT PULSE
 240 |      ════════════════════════════════════════════════════ -->
 241 | <section class="mu-section" id="mu-reddit">
 242 |   <div class="mu-section-head">
 243 |     <h2 class="mu-section-title">REDDIT PULSE</h2>
 244 |     <span class="mu-section-sub">r/bitcoin &middot; live</span>
 245 |   </div>
 246 |   <div class="mu-reddit-feed" id="reddit-feed"></div>
 247 | </section>
 248 | 
 249 | <!-- ════════════════════════════════════════════════════
 250 |      PARTNER CHANNELS TODAY
 251 |      ════════════════════════════════════════════════════ -->
 252 | <section class="mu-section" id="mu-partners">
 253 |   <div class="mu-section-head">
 254 |     <h2 class="mu-section-title">PARTNER CHANNELS TODAY</h2>
 255 |     <span class="mu-section-sub">{{ series_count }} channels tracked</span>
 256 |   </div>
 257 |   <div class="mu-partner-rail" id="partner-rail"></div>
 258 | </section>
 259 | 
 260 | <!-- ════════════════════════════════════════════════════
 261 |      ORIGINAL SERIES
 262 |      ════════════════════════════════════════════════════ -->
 263 | <section class="mu-section" id="mu-series">
 264 |   <div class="mu-section-head">
 265 |     <h2 class="mu-section-title">ORIGINAL SERIES</h2>
 266 |   </div>
 267 |   <div class="mu-series-grid">
 268 |     {% for s in series_list %}
 269 |     <a class="mu-series-item" href="https://youtube.com/watch?v={{ s.first_id }}" target="_blank" rel="noopener"
 270 |        data-thumb="https://img.youtube.com/vi/{{ s.first_id }}/maxresdefault.jpg">
 271 |       <div class="mu-series-name">{{ s.title }}</div>
 272 |       <div class="mu-series-sub">{{ s.description|upper if s.description else '' }}</div>
 273 |       <div class="mu-series-count">{{ s.ep_count }} episodes</div>
 274 |     </a>
 275 |     {% endfor %}
 276 |   </div>
 277 | </section>
 278 | 
 279 | <!-- ════════════════════════════════════════════════════
 280 |      LATEST EPISODES
 281 |      ════════════════════════════════════════════════════ -->
 282 | <section class="mu-section" id="mu-episodes">
 283 |   <div class="mu-section-head">
 284 |     <h2 class="mu-section-title">LATEST EPISODES</h2>
 285 |     <span class="mu-section-sub">{{ podcast_count }} episodes</span>
 286 |   </div>
 287 |   <div class="mu-ep-filters">
 288 |     <button class="mu-chip active" data-filter="all">All</button>
 289 |     <button class="mu-chip" data-filter="episodes">Episodes</button>
 290 |     <button class="mu-chip" data-filter="clips">Clips</button>
 291 |     <button class="mu-chip" data-filter="briefings">Briefings</button>
 292 |   </div>
 293 |   <div class="mu-ep-grid">
 294 |     {% for ep in latest_episodes[:12] %}
 295 |     {% set vid_id = ep.audio_url.split('v=')[-1].split('&')[0] if ep.audio_url and 'v=' in ep.audio_url else '' %}
 296 |     <a class="mu-ep-item" href="https://youtube.com/watch?v={{ vid_id }}" target="_blank" rel="noopener">
 297 |       <div class="mu-ep-thumb">
 298 |         <img src="https://img.youtube.com/vi/{{ vid_id }}/mqdefault.jpg" alt="{{ ep.title }}" loading="lazy" width="320" height="180">
 299 |       </div>
 300 |       <div class="mu-ep-info">
 301 |         <div class="mu-ep-title">{{ ep.title }}</div>
 302 |         <div class="mu-ep-meta">
 303 |           {{ ep.published_date.strftime('%b %d') if ep.published_date else '' }}
 304 |           {% if ep.host %} &middot; {{ ep.host }}{% endif %}
 305 |         </div>
 306 |       </div>
 307 |     </a>
 308 |     {% endfor %}
 309 |   </div>
 310 | </section>
 311 | 
 312 | <!-- ════════════════════════════════════════════════════
 313 |      THE LIBRARY
 314 |      ════════════════════════════════════════════════════ -->
 315 | <section class="mu-section" id="mu-library">
 316 |   <div class="mu-section-head">
 317 |     <h2 class="mu-section-title">THE LIBRARY</h2>
 318 |     <span class="mu-section-sub">Curated reading for sovereign minds</span>
 319 |   </div>
 320 | 
 321 |   <!-- Leaderboard + Rising Stars -->
 322 |   <div class="mu-lib-top">
 323 |     <div class="mu-lib-leaderboard">
 324 |       <div class="mu-lib-subtitle">LEADERBOARD</div>
 325 |       <div class="mu-lb-item" data-rank="1">
 326 |         <span class="mu-lb-rank">#1</span>
 327 |         <span class="mu-lb-title">The Bitcoin Standard</span>
 328 |         <span class="mu-lb-dot">&middot;</span>
 329 |         <span class="mu-lb-author">Saifedean Ammous</span>
 330 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:100%"></div></div>
 331 |         <button class="mu-vote-btn" data-book="bitcoin-standard">&#128077;</button>
 332 |         <span class="mu-vote-count" data-book="bitcoin-standard">0</span>
 333 |       </div>
 334 |       <div class="mu-lb-item" data-rank="2">
 335 |         <span class="mu-lb-rank">#2</span>
 336 |         <span class="mu-lb-title">Broken Money</span>
 337 |         <span class="mu-lb-dot">&middot;</span>
 338 |         <span class="mu-lb-author">Lyn Alden</span>
 339 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:82%"></div></div>
 340 |         <button class="mu-vote-btn" data-book="broken-money">&#128077;</button>
 341 |         <span class="mu-vote-count" data-book="broken-money">0</span>
 342 |       </div>
 343 |       <div class="mu-lb-item" data-rank="3">
 344 |         <span class="mu-lb-rank">#3</span>
 345 |         <span class="mu-lb-title">The Sovereign Individual</span>
 346 |         <span class="mu-lb-dot">&middot;</span>
 347 |         <span class="mu-lb-author">Davidson &amp; Rees-Mogg</span>
 348 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:68%"></div></div>
 349 |         <button class="mu-vote-btn" data-book="sovereign-individual">&#128077;</button>
 350 |         <span class="mu-vote-count" data-book="sovereign-individual">0</span>
 351 |       </div>
 352 |       <div class="mu-lb-item" data-rank="4">
 353 |         <span class="mu-lb-rank">#4</span>
 354 |         <span class="mu-lb-title">Mastering Bitcoin</span>
 355 |         <span class="mu-lb-dot">&middot;</span>
 356 |         <span class="mu-lb-author">Andreas Antonopoulos</span>
 357 |         <div class="mu-lb-bar"><div class="mu-lb-fill" style="width:55%"></div></div>
 358 |         <button class="mu-vote-btn" data-book="mastering-bitcoin">&#128077;</button>
 359 |         <span class="mu-vote-count" data-book="mastering-bitcoin">0</span>
 360 |       </div>
 361 |     </div>
 362 | 
 363 |     <div class="mu-lib-rising">
 364 |       <div class="mu-lib-subtitle">RISING STARS</div>
 365 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Resistance Money &middot; Andrew M. Bailey</div>
 366 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Bitcoin is Venice &middot; Allen Farrington</div>
 367 |       <div class="mu-rising-item"><span class="mu-rising-arrow">&uarr;</span> Check Your Financial Privilege &middot; Alex Gladstein</div>
 368 |     </div>
 369 |   </div>
 370 | 
 371 |   <!-- Learning Paths -->
 372 |   <div class="mu-lib-paths">
 373 |     <div class="mu-lib-subtitle">LEARNING PATHS</div>
 374 |     <div class="mu-paths-grid">
 375 |       <div class="mu-path">
 376 |         <div class="mu-path-name">UNDERSTAND MONEY</div>
 377 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1119473861" target="_blank" rel="noopener">The Bitcoin Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 378 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544526474" target="_blank" rel="noopener">The Fiat Standard <span class="mu-path-author">&middot; Saifedean Ammous</span></a>
 379 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0CN14FKHF" target="_blank" rel="noopener">Broken Money <span class="mu-path-author">&middot; Lyn Alden</span></a>
 380 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1999257405" target="_blank" rel="noopener">The Price of Tomorrow <span class="mu-path-author">&middot; Jeff Booth</span></a>
 381 |       </div>
 382 |       <div class="mu-path">
 383 |         <div class="mu-path-name">UNDERSTAND BITCOIN</div>
 384 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1098150090" target="_blank" rel="noopener">Mastering Bitcoin <span class="mu-path-author">&middot; Andreas Antonopoulos</span></a>
 385 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B07MWGP64R" target="_blank" rel="noopener">Inventing Bitcoin <span class="mu-path-author">&middot; Yan Pritzker</span></a>
 386 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B08YQMC2WM" target="_blank" rel="noopener">The Blocksize War <span class="mu-path-author">&middot; Jonathan Bier</span></a>
 387 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B0B3L61JYN" target="_blank" rel="noopener">The Genesis Book <span class="mu-path-author">&middot; Aaron van Wirdum</span></a>
 388 |       </div>
 389 |       <div class="mu-path">
 390 |         <div class="mu-path-name">UNDERSTAND FREEDOM</div>
 391 |         <a class="mu-path-book" href="https://www.amazon.com/dp/0684832720" target="_blank" rel="noopener">The Sovereign Individual <span class="mu-path-author">&middot; Davidson &amp; Rees-Mogg</span></a>
 392 |         <a class="mu-path-book" href="https://www.amazon.com/dp/1544542895" target="_blank" rel="noopener">Softwar <span class="mu-path-author">&middot; Jason Lowery</span></a>
 393 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09C4GLPYX" target="_blank" rel="noopener">Thank God for Bitcoin <span class="mu-path-author">&middot; Jimmy Song et al.</span></a>
 394 |         <a class="mu-path-book" href="https://www.amazon.com/dp/B09KLPNBPC" target="_blank" rel="noopener">Bitcoin is Venice <span class="mu-path-author">&middot; Allen Farrington</span></a>
 395 |       </div>
 396 |     </div>
 397 |   </div>
 398 | 
 399 |   <!-- Full Library (collapsed by default) -->
 400 |   <button class="mu-lib-toggle" id="lib-toggle">&darr; VIEW FULL LIBRARY</button>
 401 |   <div class="mu-lib-full" id="lib-full">
 402 |     <div class="mu-lib-grid">
 403 |       {% for book in all_books %}
 404 |       <a class="mu-lib-book" href="{{ book.amazon_url }}" target="_blank" rel="noopener">
 405 |         <div class="mu-lib-cover" style="background:{{ book.color|default('#222') }}">
 406 |           <span>{{ book.title[:40] }}</span>
 407 |         </div>
 408 |         <div class="mu-lib-book-title">{{ book.title }}</div>
 409 |         <div class="mu-lib-book-author">{{ book.author }}</div>
 410 |         <button class="mu-vote-btn" data-book="{{ book.title|lower|replace(' ','-') }}">&#128077;</button>
 411 |         <span class="mu-vote-count" data-book="{{ book.title|lower|replace(' ','-') }}">0</span>
 412 |       </a>
 413 |       {% endfor %}
 414 |     </div>
 415 |   </div>
 416 | </section>
 417 | 
 418 | <!-- ════════════════════════════════════════════════════
 419 |      NEWSLETTER CTA
 420 |      ════════════════════════════════════════════════════ -->
 421 | <section class="mu-newsletter" id="mu-newsletter">
 422 |   <h2 class="mu-nl-title">Sovereign Intel Briefing</h2>
 423 |   <p class="mu-nl-sub">Daily Bitcoin intelligence. No noise. No ads. Delivered before markets open.</p>
 424 |   <div class="mu-nl-form">
 425 |     <input type="email" placeholder="your@email.com" id="newsletter-email" autocomplete="email">
 426 |     <button id="newsletter-submit">Subscribe</button>
 427 |   </div>
 428 | </section>
 429 | 
 430 | <!-- ════════════════════════════════════════════════════
 431 |      COMMAND PALETTE (Cmd+K)
 432 |      ════════════════════════════════════════════════════ -->
 433 | <div class="mu-cmd-overlay" id="cmd-overlay">
 434 |   <div class="mu-cmd-box">
 435 |     <div class="mu-cmd-prompt">
 436 |       <span class="mu-cmd-caret">&gt;</span>
 437 |       <input class="mu-cmd-input" id="cmd-input" placeholder="" autocomplete="off" spellcheck="false">
 438 |     </div>
 439 |     <div class="mu-cmd-results" id="cmd-results"></div>
 440 |     <div class="mu-cmd-footer">Press &uarr;&darr; to navigate &middot; Enter to select &middot; Esc to close</div>
 441 |   </div>
 442 | </div>
 443 | 
 444 | <!-- ════════════════════════════════════════════════════
 445 |      AUDIO BAR (floating, hidden until active)
 446 |      ════════════════════════════════════════════════════ -->
 447 | <div class="mu-audio-bar" id="audio-bar">
 448 |   <button class="mu-ab-play" id="ab-play">&#9654;</button>
 449 |   <span class="mu-ab-info" id="ab-info"></span>
 450 |   <div class="mu-ab-progress">
 451 |     <div class="mu-ab-track">
 452 |       <div class="mu-ab-fill" id="ab-fill"></div>
 453 |       <div class="mu-ab-dot" id="ab-dot"></div>
 454 |     </div>
 455 |   </div>
 456 |   <span class="mu-ab-time" id="ab-time">0:00 / 0:00</span>
 457 |   <button class="mu-ab-speed" id="ab-speed">1&times;</button>
 458 | </div>
 459 | 
 460 | <!-- D5: Health Strip -->
 461 | <div id="health-strip" class="mu-health-strip"></div>
 462 | 
 463 | {% endblock %}
 464 | 
 465 | {% block scripts %}
 466 | <script src="/static/js/media_unified_v5.js"></script>
 467 | <script>
 468 | function subscribeNewsletter() {
 469 |   const email = document.getElementById('newsletter-email').value;
 470 |   if (!email || !email.includes('@')) { alert('Enter a valid email'); return; }
 471 |   fetch('/api/newsletter/subscribe', {
 472 |     method: 'POST',
 473 |     headers: {'Content-Type': 'application/json'},
 474 |     body: JSON.stringify({email: email})
 475 |   }).then(r => r.json()).then(d => {
 476 |     if (d.success) alert('Subscribed! Check your inbox.');
 477 |     else alert(d.message || 'Subscription failed');
 478 |   }).catch(() => alert('Network error — try again'));
 479 | }
 480 | document.getElementById('newsletter-submit')?.addEventListener('click', subscribeNewsletter);
 481 | 
 482 | // Phase 2: X Spaces + telemetry wired in media_p2_init below
 483 | </script>
 484 | 
 485 | <style>
 486 | /* ── D4: Relay Status Bar ─────────────────────── */
 487 | .mu-relay-status-bar {
 488 |   display: flex; gap: 8px; padding: 6px 12px;
 489 |   background: rgba(247,147,26,0.04); border-bottom: 1px solid #1a1a1a;
 490 |   flex-wrap: wrap;
 491 | }
 492 | .mu-relay-item {
 493 |   display: flex; align-items: center; gap: 5px;
 494 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 495 | }
 496 | .mu-relay-dot {
 497 |   width: 7px; height: 7px; border-radius: 50%;
 498 |   animation: mu-pulse 2s infinite;
 499 | }
 500 | .mu-relay-name { color: #888; letter-spacing: 1px; }
 501 | .mu-relay-status { color: #555; font-size: 8px; }
 502 | .mu-relay-count { color: #444; font-size: 8px; }
 503 | 
 504 | /* ── D3: Signal Strength Gauge ────────────────── */
 505 | .mu-signal-section { padding: 24px 0; }
 506 | .mu-signal-gauge-wrap {
 507 |   display: flex; align-items: center; gap: 40px;
 508 |   padding: 20px 0; flex-wrap: wrap;
 509 | }
 510 | #signal-strength-gauge { flex-shrink: 0; }
 511 | .mu-gauge-ring {
 512 |   position: relative; width: 140px; height: 140px;
 513 |   border-radius: 50%;
 514 |   background: conic-gradient(var(--color) var(--score), #1a1a1a 0);
 515 |   display: flex; align-items: center; justify-content: center;
 516 |   box-shadow: 0 0 24px color-mix(in srgb, var(--color) 30%, transparent);
 517 | }
 518 | .mu-gauge-inner {
 519 |   width: 100px; height: 100px; border-radius: 50%;
 520 |   background: #0a0a0a;
 521 |   display: flex; flex-direction: column;
 522 |   align-items: center; justify-content: center; gap: 2px;
 523 | }
 524 | .mu-gauge-score {
 525 |   font-family: 'Geist Mono', monospace; font-size: 30px;
 526 |   font-weight: 900; color: var(--color); line-height: 1;
 527 | }
 528 | .mu-gauge-label {
 529 |   font-family: 'Geist Mono', monospace; font-size: 8px;
 530 |   color: #555; letter-spacing: 2px;
 531 | }
 532 | .mu-gauge-level {
 533 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 534 |   font-weight: 700; color: var(--color);
 535 | }
 536 | .mu-signal-breakdown {
 537 |   display: flex; flex-direction: column; gap: 10px; min-width: 220px;
 538 | }
 539 | .mu-sig-row {
 540 |   display: flex; gap: 8px; align-items: center;
 541 |   font-family: 'Geist Mono', monospace; font-size: 11px;
 542 | }
 543 | .mu-sig-key { color: #555; letter-spacing: 1px; min-width: 90px; }
 544 | .mu-sig-val { color: #F7931A; font-weight: 700; min-width: 32px; }
 545 | .mu-sig-weight { color: #333; font-size: 9px; }
 546 | .mu-sig-total .mu-sig-key { color: #888; }
 547 | .mu-sig-total .mu-sig-val { color: #fff; font-size: 14px; }
 548 | 
 549 | /* ── D5: Health Strip ─────────────────────────── */
 550 | .mu-health-strip {
 551 |   position: fixed; bottom: 0; left: 0; right: 0;
 552 |   height: 30px; background: #050505;
 553 |   border-top: 1px solid #1a1a1a;
 554 |   display: flex; align-items: center;
 555 |   padding: 0 16px; gap: 20px; z-index: 9999;
 556 |   overflow-x: auto; overflow-y: hidden;
 557 | }
 558 | .mu-hs-item { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
 559 | .mu-hs-dot {
 560 |   width: 7px; height: 7px; border-radius: 50%;
 561 |   animation: mu-pulse 2s infinite;
 562 | }
 563 | .mu-hs-name {
 564 |   font-family: 'Geist Mono', monospace; font-size: 9px;
 565 |   color: #555; letter-spacing: 1px;
 566 | }
 567 | .mu-hs-lat {
 568 |   font-family: 'Geist Mono', monospace; font-size: 8px; color: #333;
 569 | }
 570 | @keyframes mu-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
 571 | 
 572 | /* Bottom padding so health strip doesn't cover content */
 573 | .mu-page { padding-bottom: 38px; }
 574 | </style>
 575 | 
 576 | <script>
 577 | // ═══════════════════════════════════════════════════════
 578 | // MEDIA UNIFIED — PHASE 2 RUNTIME
 579 | // D1: Clean API wiring  D2: Live telemetry  D3: Signal gauge
 580 | // D4: Nostr relay panel  D5: Health strip
 581 | // ═══════════════════════════════════════════════════════
 582 | 
 583 | (function() {
 584 |   'use strict';
 585 | 
 586 |   // ── Cache ────────────────────────────────────────────
 587 |   var _cache = { sentiment: null, spaces: null, tradfi: null };
 588 | 
 589 |   // ── D1 + D2: Live Telemetry Wiring ──────────────────
 590 |   async function fetchSentiment() {
 591 |     try {
 592 |       var r = await fetch('/api/media/sentiment');
 593 |       var d = await r.json();
 594 |       _cache.sentiment = d;
 595 |       return d;
 596 |     } catch(e) {
 597 |       console.warn('[P2] sentiment fetch failed:', e);
 598 |       return _cache.sentiment || { composite_score: null, label: 'OFFLINE' };
 599 |     }
 600 |   }
 601 | 
 602 |   async function fetchSpaces() {
 603 |     try {
 604 |       var r = await fetch('/api/spaces/live');
 605 |       var d = await r.json();
 606 |       _cache.spaces = d;
 607 |       return d;
 608 |     } catch(e) {
 609 |       console.warn('[P2] spaces fetch failed:', e);
 610 |       return _cache.spaces || { spaces: [], score: 0, label: 'OFFLINE' };
 611 |     }
 612 |   }
 613 | 
 614 |   async function fetchTradfi() {
 615 |     try {
 616 |       var r = await fetch('/api/tradfi/signals');
 617 |       var d = await r.json();
 618 |       _cache.tradfi = d;
 619 |       return d;
 620 |     } catch(e) {
 621 |       return _cache.tradfi || null;
 622 |     }
 623 |   }
 624 | 
 625 |   // ── D3: Signal Strength Gauge Renderer ──────────────
 626 |   function computeSignalStrength(sentData, spacesData) {
 627 |     var sentScore = (sentData && sentData.composite_score != null)
 628 |       ? parseFloat(sentData.composite_score) : 50;
 629 |     var spacesCount = (spacesData && spacesData.spaces)
 630 |       ? spacesData.spaces.length : 0;
 631 |     var spacesScore = Math.min(spacesCount * 10, 100);
 632 |     return Math.round(sentScore * 0.7 + spacesScore * 0.3);
 633 |   }
 634 | 
 635 |   function renderSignalGauge(score, sentScore, spacesScore) {
 636 |     var el = document.getElementById('signal-strength-gauge');
 637 |     if (!el) return;
 638 |     var level = score >= 70 ? 'HIGH' : score >= 40 ? 'MODERATE' : 'LOW';
 639 |     var color = score >= 70 ? '#F7931A' : score >= 40 ? '#E67E22' : '#666';
 640 |     el.innerHTML =
 641 |       '<div class="mu-gauge-ring" style="--score:' + score + '%;--color:' + color + '">' +
 642 |         '<div class="mu-gauge-inner">' +
 643 |           '<div class="mu-gauge-score">' + score + '</div>' +
 644 |           '<div class="mu-gauge-label">SIGNAL</div>' +
 645 |           '<div class="mu-gauge-level">' + level + '</div>' +
 646 |         '</div>' +
 647 |       '</div>';
 648 |     // Update breakdown
 649 |     var sEl = document.getElementById('sig-sentiment');
 650 |     var spEl = document.getElementById('sig-spaces');
 651 |     var cEl = document.getElementById('sig-composite');
 652 |     if (sEl) sEl.textContent = Math.round(sentScore);
 653 |     if (spEl) spEl.textContent = Math.round(Math.min((spacesScore||0)*10,100));
 654 |     if (cEl) cEl.textContent = score;
 655 |   }
 656 | 
 657 |   // ── D4: Nostr Relay Status Panel Updater ────────────
 658 |   // Hook into the existing RelayManager to sync relay dots
 659 |   function syncRelayStatusBar() {
 660 |     if (!window.relayManager || !window.relayManager.sockets) return;
 661 |     var sockets = window.relayManager.sockets;
 662 |     Object.keys(sockets).forEach(function(url) {
 663 |       var ws = sockets[url];
 664 |       var relayName = url.replace('wss://','').split('/')[0];
 665 |       var el = document.querySelector('[data-relay="' + relayName + '"]');
 666 |       if (!el) return;
 667 |       var dot = el.querySelector('.mu-relay-dot');
 668 |       var statusEl = el.querySelector('.mu-relay-status');
 669 |       var countEl = el.querySelector('.mu-relay-count');
 670 |       if (!dot || !statusEl) return;
 671 |       var rs = ws.readyState;
 672 |       if (rs === 1) { // OPEN
 673 |         dot.style.background = '#F7931A';
 674 |         statusEl.textContent = 'LIVE';
 675 |         statusEl.style.color = '#F7931A';
 676 |       } else if (rs === 0) { // CONNECTING
 677 |         dot.style.background = '#E67E22';
 678 |         statusEl.textContent = 'CONNECTING';
 679 |         statusEl.style.color = '#E67E22';
 680 |       } else {
 681 |         dot.style.background = '#444';
 682 |         statusEl.textContent = 'OFFLINE';
 683 |         statusEl.style.color = '#444';
 684 |       }
 685 |     });
 686 |     // Sync note counts from state
 687 |     if (window.state && window.state.nostrNotes) {
 688 |       var byRelay = {};
 689 |       window.state.nostrNotes.forEach(function(n) {
 690 |         if (n.relay) byRelay[n.relay] = (byRelay[n.relay]||0) + 1;
 691 |       });
 692 |       Object.keys(byRelay).forEach(function(url) {
 693 |         var relayName = url.replace('wss://','').split('/')[0];
 694 |         var el = document.querySelector('[data-relay="' + relayName + '"]');
 695 |         if (!el) return;
 696 |         var countEl = el.querySelector('.mu-relay-count');
 697 |         if (countEl) countEl.textContent = byRelay[url] + ' notes';
 698 |       });
 699 |     }
 700 |   }
 701 | 
 702 |   // ── X Spaces Telemetry Display (D1 replacement) ─────
 703 |   function updateXSpacesTelemetry(spacesData) {
 704 |     var xs = spacesData || {};
 705 |     var xsScore = xs.score != null ? xs.score : (xs.x_spaces ? xs.x_spaces.score : null);
 706 |     var xsLabel = xs.label || (xs.x_spaces ? xs.x_spaces.label : '') || '';
 707 |     var activeCount = xs.spaces ? xs.spaces.length : (xs.active_count || 0);
 708 | 
 709 |     var sc = document.getElementById('telem-xs-score');
 710 |     var lb = document.getElementById('telem-xs-label');
 711 |     var dot = document.getElementById('health-xspaces');
 712 |     if (sc && xsScore != null) sc.textContent = xsScore;
 713 |     if (lb && xsLabel) {
 714 |       lb.textContent = xsLabel;
 715 |       lb.style.color = xsLabel === 'BULLISH' ? '#22c55e'
 716 |                      : xsLabel === 'BEARISH' ? '#ef4444' : '#888';
 717 |     }
 718 |     if (dot) {
 719 |       dot.classList.remove('loading');
 720 |       dot.classList.add(activeCount > 0 ? 'connected' : 'error');
 721 |     }
 722 | 
 723 |     // Provide blend shim to existing signal engine
 724 |     window._ppBlendXSpaces = function(baseScore) {
 725 |       if (xsScore != null) return Math.round(baseScore * 0.7 + xsScore * 0.3);
 726 |       return baseScore;
 727 |     };
 728 |   }
 729 | 
 730 |   // ── D2: Master 30s Telemetry Poll ───────────────────
 731 |   async function updateTelemetry() {
 732 |     var results = await Promise.allSettled([
 733 |       fetchSentiment(),
 734 |       fetchSpaces(),
 735 |       fetchTradfi()
 736 |     ]);
 737 | 
 738 |     var sentData  = results[0].status === 'fulfilled' ? results[0].value : (_cache.sentiment || {});
 739 |     var spacesData = results[1].status === 'fulfilled' ? results[1].value : (_cache.spaces || {});
 740 | 
 741 |     // Update X Spaces display
 742 |     updateXSpacesTelemetry(spacesData);
 743 | 
 744 |     // D3: Compute + render Signal Strength gauge
 745 |     var spacesCount = spacesData.spaces ? spacesData.spaces.length : 0;
 746 |     var sentScore = sentData.composite_score != null ? parseFloat(sentData.composite_score) : 50;
 747 |     var score = computeSignalStrength(sentData, spacesData);
 748 |     renderSignalGauge(score, sentScore, spacesCount);
 749 | 
 750 |     // D4: Sync relay status bar
 751 |     syncRelayStatusBar();
 752 |   }
 753 | 
 754 |   // ── D5: Health Strip ─────────────────────────────────
 755 |   var P2_SERVICES = [
 756 |     { name: 'PIPELINE', url: 'https://relay.protocolpulse.io/health' },
 757 |     { name: 'ORACLE',   url: 'https://avatar.protocolpulse.io/health' },
 758 |     { name: 'REPLIT',   url: '/api/health' },
 759 |     { name: 'SPACES',   url: '/api/spaces/live' },
 760 |     { name: 'TRADFI',   url: '/api/tradfi/signals' },
 761 |   ];
 762 | 
 763 |   async function checkService(svc) {
 764 |     var start = Date.now();
 765 |     try {
 766 |       var r = await Promise.race([
 767 |         fetch(svc.url, { method: 'HEAD', cache: 'no-store' }),
 768 |         new Promise(function(_, rej) { setTimeout(function(){ rej(new Error('timeout')); }, 5000); })
 769 |       ]);
 770 |       return { status: r.ok ? 'UP' : 'DEGRADED', lat: Date.now() - start };
 771 |     } catch(e) {
 772 |       return { status: 'DOWN', lat: null };
 773 |     }
 774 |   }
 775 | 
 776 |   async function updateHealthStrip() {
 777 |     var strip = document.getElementById('health-strip');
 778 |     if (!strip) return;
 779 |     var results = await Promise.allSettled(P2_SERVICES.map(checkService));
 780 |     strip.innerHTML = P2_SERVICES.map(function(svc, i) {
 781 |       var r = (results[i].status === 'fulfilled' ? results[i].value : null) || { status: 'UNKNOWN', lat: null };
 782 |       var color = r.status === 'UP' ? '#27AE60' : r.status === 'DEGRADED' ? '#E67E22' : '#444';
 783 |       var lat = r.lat ? r.lat + 'ms' : '--';
 784 |       return '<div class="mu-hs-item">' +
 785 |         '<div class="mu-hs-dot" style="background:' + color + '"></div>' +
 786 |         '<span class="mu-hs-name">' + svc.name + '</span>' +
 787 |         '<span class="mu-hs-lat">' + lat + '</span>' +
 788 |       '</div>';
 789 |     }).join('');
 790 |   }
 791 | 
 792 |   // ── BOOT ─────────────────────────────────────────────
 793 |   document.addEventListener('DOMContentLoaded', function() {
 794 |     // D2+D3: initial poll + 30s interval
 795 |     updateTelemetry();
 796 |     setInterval(updateTelemetry, 30000);
 797 | 
 798 |     // D4: Relay status sync every 5s
 799 |     setInterval(syncRelayStatusBar, 5000);
 800 | 
 801 |     // D5: Health strip initial + 60s interval
 802 |     updateHealthStrip();
 803 |     setInterval(updateHealthStrip, 60000);
 804 |   });
 805 | 
 806 | })();
 807 | </script>
 808 | {% endblock %}
 809 | 
```

### File: video_pipeline_v3/dual_host_tts.py (372 lines)
```
   1 | #!/usr/bin/env python3
   2 | """dual_host_tts.py — Single-host TTS engine for Pulse Check.
   3 | 
   4 | Generates audio using ElevenLabs TTS.
   5 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) — PBX approved single narrator at 1.10x speed.
   6 | Both host=1 and host=2 entries route to Mark (single voice, no gender swap).
   7 | 
   8 | Usage:
   9 |     from dual_host_tts import generate_dialogue_audio
  10 | 
  11 |     dialogue = [
  12 |         {"host": 1, "text": "So Saylor just dropped another banger..."},
  13 |         {"host": 2, "text": "Let's roll the clip."},
  14 |         {"host": "CLIP", "duration": 30, "source": "@MicroStrategy"},
  15 |         {"host": 2, "text": "Ok here's what blows my mind about this..."},
  16 |         {"host": 1, "text": "Right, and if you think about it..."},
  17 |     ]
  18 | 
  19 |     result = generate_dialogue_audio(dialogue, output_dir="output/")
  20 |     # Returns: {
  21 |     #   "lines": [...],
  22 |     #   "full": "output/full_dialogue.m4a",
  23 |     #   "total_duration": 45.0,
  24 |     # }
  25 | """
  26 | import os
  27 | import sys
  28 | import json
  29 | import subprocess
  30 | import time
  31 | 
  32 | BASE = os.path.dirname(os.path.abspath(__file__))
  33 | sys.path.insert(0, BASE)
  34 | 
  35 | try:
  36 |     import requests
  37 |     HAS_REQUESTS = True
  38 | except ImportError:
  39 |     HAS_REQUESTS = False
  40 | 
  41 | from relay import get_key
  42 | 
  43 | # ── Voice configuration ──────────────────────────────────────────────────────
  44 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST ONLY — Mark at 1.10x speed.
  45 | # Nicole (piTKgcLEGmPE4e6mEKli) and Chris (iP95p4xoKVk53GoZ742B) are BANNED.
  46 | # Both host=1 and host=2 map to Mark.
  47 | 
  48 | _MARK_VOICE = {
  49 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  50 |     "name": "Mark",
  51 |     "model_id": "eleven_turbo_v2_5",
  52 |     "voice_settings": {
  53 |         "stability": 0.55,
  54 |         "similarity_boost": 0.80,
  55 |         "style": 0.15,
  56 |         "use_speaker_boost": True,
  57 |         "speed": 1.10,
  58 |     },
  59 | }
  60 | 
  61 | VOICES = {
  62 |     1: _MARK_VOICE,
  63 |     2: _MARK_VOICE,  # both hosts → Mark (single narrator)
  64 | }
  65 | 
  66 | SILENCE_GAP = 0.3  # seconds between speakers
  67 | MAX_CHUNK_CHARS = 4900
  68 | 
  69 | _KEY_CACHE: dict = {}
  70 | 
  71 | 
  72 | def _get_cached_key(name: str) -> str:
  73 |     if name not in _KEY_CACHE:
  74 |         k = get_key(name)
  75 |         if k:
  76 |             _KEY_CACHE[name] = k.strip()
  77 |     return _KEY_CACHE.get(name, "")
  78 | 
  79 | 
  80 | def ffprobe_duration(path: str) -> float:
  81 |     r = subprocess.run(
  82 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  83 |          "-of", "csv=p=0", path],
  84 |         capture_output=True, text=True,
  85 |     )
  86 |     try:
  87 |         return float(r.stdout.strip())
  88 |     except Exception:
  89 |         return 0.0
  90 | 
  91 | 
  92 | def _generate_silence(output_path: str, duration: float) -> bool:
  93 |     r = subprocess.run(
  94 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  95 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  96 |          "-c:a", "aac", "-b:a", "192k", output_path],
  97 |         capture_output=True, text=True, timeout=30,
  98 |     )
  99 |     return r.returncode == 0 and os.path.exists(output_path)
 100 | 
 101 | 
 102 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
 103 |     r = subprocess.run(
 104 |         ["ffmpeg", "-y", "-i", mp3_path,
 105 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
 106 |         capture_output=True, text=True, timeout=120,
 107 |     )
 108 |     return r.returncode == 0 and os.path.exists(m4a_path)
 109 | 
 110 | 
 111 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
 112 |     if len(text) <= max_chars:
 113 |         return [text]
 114 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
 115 |     sentences = raw.split("\x00")
 116 |     chunks, current = [], ""
 117 |     for sent in sentences:
 118 |         if len(current) + len(sent) + 1 <= max_chars:
 119 |             current = f"{current} {sent}".strip() if current else sent
 120 |         else:
 121 |             if current:
 122 |                 chunks.append(current)
 123 |             current = sent
 124 |     if current:
 125 |         chunks.append(current)
 126 |     return [c for c in chunks if c.strip()]
 127 | 
 128 | 
 129 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 130 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback (quota exhausted)."""
 131 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 132 |     r = subprocess.run([
 133 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 134 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 135 |         output_path,
 136 |     ], capture_output=True, text=True, timeout=15)
 137 |     if r.returncode == 0 and os.path.exists(output_path):
 138 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 139 |         return True
 140 |     return False
 141 | 
 142 | 
 143 | def tts_elevenlabs(text: str, output_path: str, host: int = 1) -> bool:
 144 |     """Generate TTS audio for a single line using the specified host voice.
 145 | 
 146 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 147 |     """
 148 |     if not HAS_REQUESTS:
 149 |         return _tts_generate_silence_fallback(text, output_path)
 150 | 
 151 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 152 |     if not key:
 153 |         return _tts_generate_silence_fallback(text, output_path)
 154 | 
 155 |     voice = VOICES.get(host, VOICES[1])
 156 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 157 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 158 | 
 159 |     chunks = _chunk_text(text)
 160 |     chunk_files = []
 161 | 
 162 |     for ci, chunk in enumerate(chunks):
 163 |         # Extract speed (top-level ElevenLabs param) from voice_settings if present
 164 |         raw_settings = dict(voice["voice_settings"])
 165 |         speed_val = raw_settings.pop("speed", None)
 166 |         body = {
 167 |             "text": chunk,
 168 |             "model_id": voice["model_id"],
 169 |             "voice_settings": raw_settings,
 170 |         }
 171 |         if speed_val is not None:
 172 |             body["speed"] = speed_val
 173 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 174 |         success = False
 175 | 
 176 |         for attempt in range(3):
 177 |             try:
 178 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 179 |                 if r.status_code == 200:
 180 |                     with open(mp3_tmp, "wb") as f:
 181 |                         f.write(r.content)
 182 |                     success = True
 183 |                     break
 184 |                 elif r.status_code == 429:
 185 |                     wait = 2 ** attempt
 186 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 187 |                     time.sleep(wait)
 188 |                 else:
 189 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 190 |                     if attempt < 2:
 191 |                         time.sleep(2 ** attempt)
 192 |             except Exception as e:
 193 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 194 |                 if attempt < 2:
 195 |                     time.sleep(2 ** attempt)
 196 | 
 197 |         if not success:
 198 |             for f in chunk_files:
 199 |                 try:
 200 |                     os.remove(f)
 201 |                 except Exception:
 202 |                     pass
 203 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 204 |             print(f"  [tts] ElevenLabs failed — trying pyttsx3 fallback")
 205 |             try:
 206 |                 import pyttsx3
 207 |                 _engine = pyttsx3.init()
 208 |                 _engine.setProperty("rate", 150)
 209 |                 wav_tmp = output_path + ".pyttsx3.wav"
 210 |                 _engine.save_to_file(chunk, wav_tmp)
 211 |                 _engine.runAndWait()
 212 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 213 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 214 |                     try:
 215 |                         os.remove(wav_tmp)
 216 |                     except Exception:
 217 |                         pass
 218 |                     if ok:
 219 |                         return ok
 220 |             except Exception as pyttsx_err:
 221 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 222 |             return _tts_generate_silence_fallback(text, output_path)
 223 |         chunk_files.append(mp3_tmp)
 224 | 
 225 |     if len(chunk_files) == 1:
 226 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 227 |         try:
 228 |             os.remove(chunk_files[0])
 229 |         except Exception:
 230 |             pass
 231 |         return ok
 232 | 
 233 |     # Multi-chunk concat
 234 |     concat_list = output_path + ".concat.txt"
 235 |     mp3_combined = output_path + ".combined.mp3"
 236 |     with open(concat_list, "w") as f:
 237 |         for p in chunk_files:
 238 |             f.write(f"file '{os.path.abspath(p)}'\n")
 239 |     subprocess.run(
 240 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 241 |          "-c", "copy", mp3_combined],
 242 |         capture_output=True, text=True,
 243 |     )
 244 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 245 |     for f in chunk_files + [concat_list, mp3_combined]:
 246 |         try:
 247 |             if os.path.exists(f):
 248 |                 os.remove(f)
 249 |         except Exception:
 250 |             pass
 251 |     return ok
 252 | 
 253 | 
 254 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 255 |     """Generate audio for the entire dual-host dialogue.
 256 | 
 257 |     Args:
 258 |         dialogue: List of dicts with keys:
 259 |             - host: 1 or 2 (both route to Mark), or "CLIP" (silence placeholder)
 260 |             - text: The line text (or clip description for CLIP)
 261 |             - duration: (CLIP only) silence duration in seconds
 262 |             - source: (CLIP only) source channel name
 263 | 
 264 |     Returns:
 265 |         {
 266 |             "lines": [
 267 |                 {"path": str, "host": int|"CLIP", "duration": float,
 268 |                  "start": float, "text": str},
 269 |                 ...
 270 |             ],
 271 |             "full": str,          # path to concatenated audio
 272 |             "total_duration": float,
 273 |         }
 274 |     """
 275 |     os.makedirs(output_dir, exist_ok=True)
 276 | 
 277 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 278 |     if not key:
 279 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 280 | 
 281 |     silence_path = os.path.join(output_dir, "silence.m4a")
 282 |     _generate_silence(silence_path, SILENCE_GAP)
 283 | 
 284 |     lines = []
 285 |     parts_for_concat = []
 286 |     current_time = 0.0
 287 | 
 288 |     for i, entry in enumerate(dialogue):
 289 |         host = entry.get("host")
 290 |         text = entry.get("text", "")
 291 | 
 292 |         if host == "CLIP":
 293 |             clip_dur = entry.get("duration", 0)
 294 |             lines.append({
 295 |                 "path": None,
 296 |                 "host": "CLIP",
 297 |                 "duration": clip_dur,
 298 |                 "start": current_time,
 299 |                 "source": entry.get("source", ""),
 300 |                 "query": entry.get("query", ""),
 301 |                 "text": text,
 302 |             })
 303 |             continue
 304 | 
 305 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 306 |         voice = VOICES.get(host_num, VOICES[1])
 307 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 308 | 
 309 |         print(f"  [tts] Line {i:02d} ({voice['name']}): {text[:60]}...")
 310 | 
 311 |         if tts_elevenlabs(text, line_path, host_num):
 312 |             dur = ffprobe_duration(line_path)
 313 |             lines.append({
 314 |                 "path": line_path,
 315 |                 "host": host_num,
 316 |                 "duration": dur,
 317 |                 "start": current_time,
 318 |                 "text": text,
 319 |             })
 320 |             parts_for_concat.append(line_path)
 321 |             current_time += dur
 322 | 
 323 |             if i < len(dialogue) - 1:
 324 |                 parts_for_concat.append(silence_path)
 325 |                 current_time += SILENCE_GAP
 326 |         else:
 327 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": host_num,
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "text": text,
 334 |             })
 335 | 
 336 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 337 |     if parts_for_concat:
 338 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 339 |         with open(concat_file, "w") as f:
 340 |             for p in parts_for_concat:
 341 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 342 |         subprocess.run(
 343 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 344 |              "-c", "copy", full_path],
 345 |             capture_output=True, text=True,
 346 |         )
 347 |         if os.path.exists(concat_file):
 348 |             os.remove(concat_file)
 349 | 
 350 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 351 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 352 | 
 353 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 354 | 
 355 |     return {
 356 |         "lines": lines,
 357 |         "full": full_path if os.path.exists(full_path) else None,
 358 |         "total_duration": total_dur,
 359 |     }
 360 | 
 361 | 
 362 | if __name__ == "__main__":
 363 |     from script_writer import generate_script
 364 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 365 |     script = generate_script(style=style)
 366 |     audio_dir = os.path.join(BASE, "output", "audio_test")
 367 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 368 |     print(json.dumps(
 369 |         {k: v for k, v in result.items() if k != "lines"},
 370 |         indent=2,
 371 |     ))
 372 | 
```

### File: video_pipeline_v3/tts_engine.py (420 lines)
```
   1 | #!/usr/bin/env python3
   2 | """TTS Engine V6 — Single-host Mark broadcast voice.
   3 | Host: Mark (1SM7GgM6IMuvQlz2BwM3) at 1.10x speed — PBX approved sole narrator.
   4 | Both host=1 and host=2 route to Mark (no gender swap, no dual-host).
   5 | Generates per-line audio with 0.3s silence gaps."""
   6 | import os, sys, json, subprocess, tempfile, time, struct
   7 | from pathlib import Path
   8 | 
   9 | try:
  10 |     import requests
  11 |     HAS_REQUESTS = True
  12 | except ImportError:
  13 |     HAS_REQUESTS = False
  14 | 
  15 | from relay import get_key
  16 | 
  17 | # PBX DIRECTIVE 2026-03-09: SINGLE HOST — Mark at 1.10x speed.
  18 | # Both host=1 and host=2 map to Mark. Deborah/Brian/Nicole/Chris are all BANNED.
  19 | _MARK_VOICE = {
  20 |     "voice_id": "1SM7GgM6IMuvQlz2BwM3",
  21 |     "name": "Mark",
  22 |     "model_id": "eleven_turbo_v2_5",
  23 |     "speed": 1.10,
  24 |     "voice_settings": {
  25 |         "stability": 0.55,
  26 |         "similarity_boost": 0.80,
  27 |         "style": 0.15,
  28 |         "use_speaker_boost": True,
  29 |     },
  30 | }
  31 | 
  32 | VOICES = {
  33 |     1: _MARK_VOICE,
  34 |     2: _MARK_VOICE,  # single narrator — both hosts are Mark
  35 | }
  36 | 
  37 | # Voice mode overrides for Mark (segment-type tuning)
  38 | VOICE_MODES = {
  39 |     "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18, "speed": 1.10},
  40 |     "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  41 |     "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15, "speed": 1.10},
  42 |     "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18, "speed": 1.10},
  43 |     "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20, "speed": 1.08},
  44 |     "data":            {"stability": 0.60, "similarity_boost": 0.82, "style": 0.12, "speed": 1.10},
  45 | }
  46 | 
  47 | SILENCE_GAP = 0.3  # seconds between speakers
  48 | MAX_CHUNK_CHARS = 4900
  49 | 
  50 | _KEY_CACHE: dict = {}
  51 | 
  52 | 
  53 | def _get_cached_key(name: str) -> str:
  54 |     if name not in _KEY_CACHE:
  55 |         k = get_key(name)
  56 |         if k:
  57 |             _KEY_CACHE[name] = k.strip()
  58 |     return _KEY_CACHE.get(name, "")
  59 | 
  60 | 
  61 | def ffprobe_duration(path: str) -> float:
  62 |     r = subprocess.run(
  63 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  64 |          "-of", "csv=p=0", path],
  65 |         capture_output=True, text=True,
  66 |     )
  67 |     try:
  68 |         return float(r.stdout.strip())
  69 |     except Exception:
  70 |         return 0.0
  71 | 
  72 | 
  73 | def _generate_silence(output_path: str, duration: float) -> bool:
  74 |     """Generate a silent audio file."""
  75 |     r = subprocess.run(
  76 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
  77 |          f"anullsrc=r=44100:cl=mono", "-t", str(duration),
  78 |          "-c:a", "aac", "-b:a", "192k", output_path],
  79 |         capture_output=True, text=True, timeout=30,
  80 |     )
  81 |     return r.returncode == 0 and os.path.exists(output_path)
  82 | 
  83 | 
  84 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
  85 |     r = subprocess.run(
  86 |         ["ffmpeg", "-y", "-i", mp3_path,
  87 |          "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
  88 |         capture_output=True, text=True, timeout=120,
  89 |     )
  90 |     return r.returncode == 0 and os.path.exists(m4a_path)
  91 | 
  92 | 
  93 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
  94 |     if len(text) <= max_chars:
  95 |         return [text]
  96 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
  97 |     sentences = raw.split("\x00")
  98 |     chunks, current = [], ""
  99 |     for sent in sentences:
 100 |         if len(current) + len(sent) + 1 <= max_chars:
 101 |             current = f"{current} {sent}".strip() if current else sent
 102 |         else:
 103 |             if current:
 104 |                 chunks.append(current)
 105 |             current = sent
 106 |     if current:
 107 |         chunks.append(current)
 108 |     return [c for c in chunks if c.strip()]
 109 | 
 110 | 
 111 | TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
 112 | 
 113 | 
 114 | def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
 115 |     """SHA256 hash of text+voice+segment_type → stable cache key."""
 116 |     import hashlib
 117 |     payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
 118 |     return hashlib.sha256(payload).hexdigest()[:16]
 119 | 
 120 | 
 121 | def _tts_cache_get(cache_key: str, output_path: str) -> bool:
 122 |     """Check TTS cache and copy to output_path if hit. Returns True on hit."""
 123 |     import shutil
 124 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 125 |     if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000:
 126 |         shutil.copy2(cache_file, output_path)
 127 |         return True
 128 |     return False
 129 | 
 130 | 
 131 | def _tts_cache_put(cache_key: str, audio_path: str) -> None:
 132 |     """Save audio to TTS cache for future runs."""
 133 |     import shutil
 134 |     os.makedirs(TTS_CACHE_DIR, exist_ok=True)
 135 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 136 |     if not os.path.exists(cache_file):
 137 |         shutil.copy2(audio_path, cache_file)
 138 | 
 139 | 
 140 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 141 |     """BUG1 FIX A: Generate silence as last-resort TTS fallback when ElevenLabs quota is exhausted.
 142 | 
 143 |     Estimates duration from text length (~12.5 chars/sec speech rate).
 144 |     Called when both ElevenLabs AND pyttsx3 fail.
 145 |     """
 146 |     dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
 147 |     r = subprocess.run([
 148 |         "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 149 |         "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 150 |         output_path,
 151 |     ], capture_output=True, text=True, timeout=15)
 152 |     if r.returncode == 0 and os.path.exists(output_path):
 153 |         print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
 154 |         return True
 155 |     return False
 156 | 
 157 | 
 158 | def tts_elevenlabs(text: str, output_path: str, host: int = 1,
 159 |                    segment_type: str = "") -> bool:
 160 |     """Generate TTS for a single line using the specified host voice.
 161 | 
 162 |     Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
 163 |     copies cached audio — no ElevenLabs API call. On miss, generates and caches.
 164 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
 165 |     """
 166 |     if not HAS_REQUESTS:
 167 |         # No requests lib — try pyttsx3 or silence
 168 |         return _tts_generate_silence_fallback(text, output_path)
 169 | 
 170 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 171 |     if not key:
 172 |         return _tts_generate_silence_fallback(text, output_path)
 173 | 
 174 |     voice = VOICES.get(host, VOICES[1])
 175 |     # Check TTS cache first — avoid API call if same text+voice was generated before
 176 |     cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
 177 |     if _tts_cache_get(cache_key, output_path):
 178 |         print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
 179 |         return True
 180 | 
 181 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
 182 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
 183 | 
 184 |     # Apply hybrid voice mode for Mark based on segment type
 185 |     voice_settings = dict(voice["voice_settings"])
 186 |     if host == 1 and segment_type in VOICE_MODES:
 187 |         mode = VOICE_MODES[segment_type]
 188 |         for k, v in mode.items():
 189 |             if k != "speed":
 190 |                 voice_settings[k] = v
 191 | 
 192 |     chunks = _chunk_text(text)
 193 |     chunk_files = []
 194 | 
 195 |     for ci, chunk in enumerate(chunks):
 196 |         body = {
 197 |             "text": chunk,
 198 |             "model_id": voice["model_id"],
 199 |             "voice_settings": voice_settings,
 200 |         }
 201 |         # Add speed parameter — use mode-specific speed for Host 1
 202 |         speed = voice.get("speed", 1.0)
 203 |         if host == 1 and segment_type in VOICE_MODES:
 204 |             speed = VOICE_MODES[segment_type].get("speed", speed)
 205 |         if speed != 1.0:
 206 |             body["speed"] = speed
 207 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
 208 |         success = False
 209 | 
 210 |         for attempt in range(3):
 211 |             try:
 212 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
 213 |                 if r.status_code == 200:
 214 |                     with open(mp3_tmp, "wb") as f:
 215 |                         f.write(r.content)
 216 |                     success = True
 217 |                     break
 218 |                 elif r.status_code == 429:
 219 |                     wait = 2 ** attempt
 220 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
 221 |                     time.sleep(wait)
 222 |                 else:
 223 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
 224 |                     if attempt < 2:
 225 |                         time.sleep(2 ** attempt)
 226 |             except Exception as e:
 227 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
 228 |                 if attempt < 2:
 229 |                     time.sleep(2 ** attempt)
 230 | 
 231 |         if not success:
 232 |             for f in chunk_files:
 233 |                 try:
 234 |                     os.remove(f)
 235 |                 except Exception:
 236 |                     pass
 237 |             # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
 238 |             print(f"  [tts] ElevenLabs failed for chunk {ci} — trying pyttsx3 fallback")
 239 |             try:
 240 |                 import pyttsx3
 241 |                 _engine = pyttsx3.init()
 242 |                 _engine.setProperty("rate", 150)
 243 |                 wav_tmp = output_path + f".pyttsx3.wav"
 244 |                 _engine.save_to_file(chunk, wav_tmp)
 245 |                 _engine.runAndWait()
 246 |                 if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
 247 |                     ok = _mp3_to_m4a(wav_tmp, output_path)
 248 |                     try:
 249 |                         os.remove(wav_tmp)
 250 |                     except Exception:
 251 |                         pass
 252 |                     if ok:
 253 |                         print(f"  [tts] pyttsx3 fallback SUCCESS for chunk {ci}")
 254 |                         return ok
 255 |             except Exception as pyttsx_err:
 256 |                 print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
 257 |             # Final fallback: generate silence so the segment still renders
 258 |             return _tts_generate_silence_fallback(text, output_path)
 259 |         chunk_files.append(mp3_tmp)
 260 | 
 261 |     # Single chunk
 262 |     if len(chunk_files) == 1:
 263 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
 264 |         try:
 265 |             os.remove(chunk_files[0])
 266 |         except Exception:
 267 |             pass
 268 |         if ok and os.path.exists(output_path):
 269 |             _tts_cache_put(cache_key, output_path)
 270 |         return ok
 271 | 
 272 |     # Multi-chunk concat
 273 |     concat_list = output_path + ".concat.txt"
 274 |     mp3_combined = output_path + ".combined.mp3"
 275 |     with open(concat_list, "w") as f:
 276 |         for p in chunk_files:
 277 |             f.write(f"file '{os.path.abspath(p)}'\n")
 278 |     subprocess.run(
 279 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 280 |          "-c", "copy", mp3_combined],
 281 |         capture_output=True, text=True,
 282 |     )
 283 |     ok = _mp3_to_m4a(mp3_combined, output_path)
 284 |     for f in chunk_files + [concat_list, mp3_combined]:
 285 |         try:
 286 |             if os.path.exists(f):
 287 |                 os.remove(f)
 288 |         except Exception:
 289 |             pass
 290 |     if ok and os.path.exists(output_path):
 291 |         _tts_cache_put(cache_key, output_path)
 292 |     return ok
 293 | 
 294 | 
 295 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
 296 |     """Generate audio for the entire dual-host dialogue.
 297 | 
 298 |     Args:
 299 |         dialogue: List of {host: 1|2|"CLIP", text: "..."}
 300 |         output_dir: Directory for audio files
 301 | 
 302 |     Returns:
 303 |         {
 304 |             "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
 305 |             "full": str,  # path to concatenated full audio
 306 |             "total_duration": float,
 307 |         }
 308 |     """
 309 |     os.makedirs(output_dir, exist_ok=True)
 310 | 
 311 |     key = _get_cached_key("ELEVENLABS_API_KEY")
 312 |     if not key:
 313 |         raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
 314 | 
 315 |     silence_path = os.path.join(output_dir, "silence.m4a")
 316 |     _generate_silence(silence_path, SILENCE_GAP)
 317 | 
 318 |     lines = []
 319 |     parts_for_concat = []
 320 |     current_time = 0.0
 321 | 
 322 |     for i, entry in enumerate(dialogue):
 323 |         host = entry.get("host")
 324 |         text = entry.get("text", "")
 325 | 
 326 |         # Skip CLIP markers — they don't have audio
 327 |         if host == "CLIP":
 328 |             lines.append({
 329 |                 "path": None,
 330 |                 "host": "CLIP",
 331 |                 "duration": 0.0,
 332 |                 "start": current_time,
 333 |                 "source": entry.get("source", ""),
 334 |                 "query": entry.get("query", ""),
 335 |                 "text": text,
 336 |             })
 337 |             continue
 338 | 
 339 |         host_num = int(host) if host in (1, 2, "1", "2") else 1
 340 |         voice = VOICES.get(host_num, VOICES[1])
 341 |         segment_type = entry.get("type", "")
 342 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
 343 | 
 344 |         mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
 345 |         print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")
 346 | 
 347 |         if tts_elevenlabs(text, line_path, host_num, segment_type=segment_type):
 348 |             dur = ffprobe_duration(line_path)
 349 |             lines.append({
 350 |                 "path": line_path,
 351 |                 "host": host_num,
 352 |                 "duration": dur,
 353 |                 "start": current_time,
 354 |                 "text": text,
 355 |             })
 356 |             parts_for_concat.append(line_path)
 357 |             current_time += dur
 358 | 
 359 |             # Add silence gap between speakers (not after last line)
 360 |             if i < len(dialogue) - 1:
 361 |                 parts_for_concat.append(silence_path)
 362 |                 current_time += SILENCE_GAP
 363 |         else:
 364 |             print(f"  [tts] FAILED line {i} ({voice['name']})")
 365 |             lines.append({
 366 |                 "path": None,
 367 |                 "host": host_num,
 368 |                 "duration": 0.0,
 369 |                 "start": current_time,
 370 |                 "text": text,
 371 |             })
 372 | 
 373 |     # Concatenate all lines into full audio
 374 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
 375 |     if parts_for_concat:
 376 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
 377 |         with open(concat_file, "w") as f:
 378 |             for p in parts_for_concat:
 379 |                 f.write(f"file '{os.path.abspath(p)}'\n")
 380 |         subprocess.run(
 381 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
 382 |              "-c", "copy", full_path],
 383 |             capture_output=True, text=True,
 384 |         )
 385 |         if os.path.exists(concat_file):
 386 |             os.remove(concat_file)
 387 | 
 388 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
 389 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
 390 | 
 391 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
 392 | 
 393 |     return {
 394 |         "lines": lines,
 395 |         "full": full_path if os.path.exists(full_path) else None,
 396 |         "total_duration": total_dur,
 397 |     }
 398 | 
 399 | 
 400 | # Legacy compatibility — V3 pipeline used generate_all_audio
 401 | def generate_all_audio(script: dict, output_dir: str) -> dict:
 402 |     """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
 403 |     if "dialogue" in script:
 404 |         return generate_dialogue_audio(script["dialogue"], output_dir)
 405 |     # V3 fallback
 406 |     raise RuntimeError("V4 pipeline requires dialogue-format script")
 407 | 
 408 | 
 409 | if __name__ == "__main__":
 410 |     from script_writer import generate_script
 411 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
 412 |     script = generate_script(style=style)
 413 |     base = os.path.dirname(os.path.abspath(__file__))
 414 |     audio_dir = os.path.join(base, "output", "audio_test")
 415 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
 416 |     print(json.dumps(
 417 |         {k: v for k, v in result.items() if k != "lines"},
 418 |         indent=2,
 419 |     ))
 420 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
