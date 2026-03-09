# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.

# PROTOCOL PULSE — GOSPEL: P3 AFFILIATE INTEGRATION
# Branch: feature/p3-affiliates | Created: 2026-03-09

---

## WHAT THIS IS
Passive revenue from two partner programs:
- Meanwhile Bitcoin Life Insurance — referralCode=KKM73K
- RNS.ID Palau Digital Residency — $300/referral

Includes: landing pages, AI-powered contextual injection on articles,
click tracking, A/B testing framework, conversion analytics.

## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY)
Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-affiliates --phase0
Ask all 3 LLMs: "What are the most effective affiliate marketing techniques for a
premium Bitcoin media audience in 2026? What makes CTAs convert without feeling
spammy or breaking trust with a cypherpunk-adjacent audience?"
Incorporate top P0 ideas before building.

## THE LAWS
### LAW 1: Contextual relevance only — no random banner spam
Claude Haiku analyzes article content → decides if this article warrants an affiliate CTA
Meanwhile CTA: only on articles tagged wealth/insurance/sovereignty/estate-planning
RNS.ID CTA: only on articles tagged regulation/privacy/sovereignty/residency/global
Never show both CTAs on same article. Never show CTAs on breaking news articles.

### LAW 2: A/B test every CTA variant
50/50 random split per user session (based on hash of IP+date, not localStorage)
Variant A: text-only subtle mention
Variant B: visual card with image/icon
Track separately. After 200 clicks per variant: evaluate winner, keep winner.
Store variant assignment + click outcome in affiliate_clicks table.

### LAW 3: Click tracking hashes IPs — never store raw
SHA256(ip + date + salt) → user_hash. Salt = random 32-byte value in .env as TRACKING_SALT.
Never store: raw IPs, cookies, user IDs. Privacy-first.

### LAW 4: Editorial voice — never feel like ads
Meanwhile landing page: PBX-voice editorial (Matty Ice tone) — "why I trust Meanwhile"
RNS.ID landing page: Protocol Pulse endorsement — "digital sovereignty starts with ID"
Both pages have clear disclaimers: "Paid affiliate partnership."
CTAs embedded in article text should read naturally: "...which is why tools like Meanwhile..."

## ARCHITECTURE

### Database
```sql
CREATE TABLE IF NOT EXISTS affiliate_clicks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  partner TEXT NOT NULL,             -- meanwhile|rns_id
  referrer_page TEXT,                -- /articles/123, /mining, etc.
  ab_variant TEXT,                   -- A|B
  converted INTEGER DEFAULT 0,       -- 1 if they reached partner site (redirect tracked)
  user_hash TEXT,                    -- SHA256(ip+date+salt)
  user_agent_hash TEXT,              -- SHA256(user_agent)
  clicked_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS affiliate_ab_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  partner TEXT NOT NULL,
  variant TEXT NOT NULL,
  impressions INTEGER DEFAULT 0,
  clicks INTEGER DEFAULT 0,
  calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aff_partner_date ON affiliate_clicks(partner, clicked_at);
```

### Routes
```python
GET  /go/meanwhile              → track click → redirect to Meanwhile with referral code
GET  /go/rns                    → track click → redirect to RNS.ID with referral code
GET  /bitcoin-life-insurance    → Meanwhile landing page
GET  /digital-residency         → RNS.ID landing page
GET  /admin/affiliates          → admin analytics dashboard
GET  /api/affiliates/metrics    → JSON: clicks/day, conversion rate, top pages
POST /api/affiliates/impression → track impression (JS beacon call on page load)
```

### AI Contextual Injection — services/affiliate_injector.py
inject_affiliate_cta(article_id, article_content) → Optional[dict]:
  1. Use claude-haiku-4-5 to classify article tags/themes
  2. Check: does this article qualify for Meanwhile? for RNS.ID?
  3. If yes: determine A/B variant (hash-based, no session/cookie needed)
  4. Return: {partner, variant, cta_html} or None

  Called by: article_detail route (articles/{id}) — inject into template context
  CTA is NEVER shown more than once per article. NEVER on homepage/list pages.
  Only on dedicated article view pages.

### Meanwhile Landing Page — /bitcoin-life-insurance
template: bitcoin_life_insurance.html

DESIGN: Dark, sophisticated, wealth-focused. Black + deep navy + gold accents.

SECTIONS:
Hero: "Your Bitcoin Legacy Deserves Protection"
  Subhead: "Life insurance denominated in Bitcoin — not fiat. Not stocks. Bitcoin."
  CTA: "Get Your Quote →" (red button, tracks click)

Why It Matters (3 cards):
  "Death benefit in BTC — your family inherits sovereignty, not a check"
  "No fiat conversion risk — benefit doesn't lose purchasing power"
  "Self-sovereign planning — outside the traditional insurance industry"

How Meanwhile Works:
  Whole life product. BTC-denominated policy. Issued by regulated insurer.
  Application online. Benefit paid in BTC directly to wallet.

Editorial Section — "Why Protocol Pulse Partners With Meanwhile":
  Matty Ice/PBX first-person voice. 3 paragraphs. Authentic endorsement.
  Not a paid ad disguised as editorial — clearly labeled "Affiliate Partnership"
  but written with genuine Protocol Pulse voice.

FAQ (6 questions):
  "Who is Meanwhile?" / "Is this regulated?" / "How is the benefit paid?"
  "What happens to the BTC if price drops?" / "Is there a medical exam?"
  "What coverage amounts are available?"

CTA Footer: "Start Your Application" → /go/meanwhile

Disclaimer: "Protocol Pulse may earn compensation when you apply through our link.
This is not financial advice."

### RNS.ID Landing Page — /digital-residency
template: digital_residency.html

DESIGN: Dark, global, freedom-focused. Black + deep blue + green accents.
Think: passport aesthetic, global citizen, sovereignty signal.

SECTIONS:
Hero: "Establish Your Digital Sovereignty — Palau Digital Residency"
  Subhead: "A government-issued digital ID outside the traditional financial surveillance state."
  CTA: "Apply Now →" (green button, tracks click)

What Is Palau Digital Residency?
  Official digital identity issued by the Republic of Palau
  Not crypto — real government-backed digital resident status
  Enables: international banking access, digital identity verification, mobility

Why Bitcoiners Care (4 points):
  Bitcoin-friendly jurisdiction | Tax optimization potential
  Privacy from surveillance finance | Geographic diversification of identity

Protocol Pulse endorsement: cypherpunk angle, sovereignty angle, PBX voice
Disclaimer: "Affiliate partnership."

FAQ: 5 questions covering legitimacy, banking, tax implications, process

CTA: "Apply for Digital Residency →" → /go/rns

### Admin Analytics — /admin/affiliates
Dashboard with:
- Summary: total clicks (30d), meanwhile clicks, rns clicks, estimated earnings
- Clicks per day chart (Canvas, last 30 days, both partners)
- Top referrer pages (which articles/pages drive most clicks)
- A/B test results: variant A vs B click rates per partner, statistical significance
- "Declare winner" button: locks in winning variant permanently

### CTA Variants
Variant A (text/inline):
  "Tools like <a href="/bitcoin-life-insurance">Meanwhile</a> let Bitcoiners
   protect generational wealth with BTC-denominated life insurance."

Variant B (card):
  Dark glass card, left red border, Meanwhile logo (text), 2-line pitch, "Learn More →"

## VERIFICATION
- [ ] GET /bitcoin-life-insurance → HTTP 200, editorial content loads
- [ ] GET /digital-residency → HTTP 200, editorial content loads
- [ ] GET /go/meanwhile → click logged to DB, redirects with referral code
- [ ] GET /go/rns → click logged to DB, redirects with referral code
- [ ] inject_affiliate_cta() returns CTA for relevant articles, None for irrelevant
- [ ] A/B variant assigned consistently for same user
- [ ] GET /admin/affiliates → shows click analytics
- [ ] IP is never stored raw (only hash in DB)
- [ ] Disclaimer present on both landing pages
- [ ] regression_test.sh: zero FAILs
- [ ] git commit + push to origin feature/p3-affiliates
