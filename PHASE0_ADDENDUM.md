# PHASE 0 ADDENDUM — p3-affiliates
# Created: 2026-03-09
# Source: C0_SYNTHESIS.md + C0_GEMINI.md + C0_GROK.md

## TOP PHASE 0 SUGGESTIONS TO IMPLEMENT

### 1. Thompson Sampling MAB (Multi-Armed Bandit) — IMPLEMENTING
**What:** Replace static 50/50 split with adaptive traffic allocation after sufficient data
**How:**
- `p3_affiliate_ab_results` table stores alpha/beta params for Thompson Sampling
- Variant selection: deterministic hash of (IP+date+salt) maps into MAB-weighted bucket
- After 100 clicks per partner: Thompson Sampling weights update automatically
- Starts 50/50, converges to winner over time
- "Declare winner" button freezes allocation permanently
- `_get_ab_variant(partner, user_hash)` in affiliate_injector.py implements this

### 2. Client-Side Behavioral Intent Scoring — IMPLEMENTING (lightweight JS, no TF.js)
**What:** Track scroll depth + time-on-page to score user intent before showing CTA
**How:**
- Pure vanilla JS in article_detail.html
- Tracks: scroll depth (0-100%), time on page (seconds), mouse movement
- Generates intent score 0-100: (scroll_depth * 0.6 + min(time_secs/120, 1)*40)
- CTA only injects via JS reveal when intent_score >= 40 (configurable threshold)
- No TF.js / no external ML - privacy-safe, pure math
- Falls back to showing CTA at page load if JS disabled

### 3. navigator.sendBeacon for Impressions — IMPLEMENTING
**What:** Non-blocking async impression tracking that doesn't delay page transitions
**How:**
- `window.addEventListener('beforeunload', ...)` fires sendBeacon to /api/affiliates/impression
- Also fires on CTA visibility (IntersectionObserver)
- Server endpoint handles beacon asynchronously

### 4. Statistical Significance Display — IMPLEMENTING
**What:** Admin dashboard shows p-value and confidence interval for A/B tests
**How:**
- Python: scipy-style z-test for two proportions (manual math, no scipy dep)
- Formula: z = (p1-p2) / sqrt(pooled*(1-pooled)*(1/n1+1/n2))
- p-value approximated via error function
- Shows: "95% confidence: Variant A wins" or "Need more data (N=47/200)"

### 5. Content-to-Conversion Intelligence in Admin — IMPLEMENTING
**What:** Show which articles drive most conversions with per-article revenue estimates
**How:**
- Admin dashboard: "Top referrer pages" table with clicks + estimated revenue
- Meanwhile: $150 average commission per funded policy (conservative)
- RNS.ID: $300 per referral (stated in gospel)
- Shows: estimated earnings per article, per day

### 6. Sovereignty Score Widget on Landing Pages — IMPLEMENTING
**What:** Visual trust score showing why Protocol Pulse endorses each partner
**How:**
- Static widget with 5 criteria: Privacy, Non-custodial, BTC-native, Regulatory, Transparency
- Score 0-5 bars, gold fill, visible on both landing pages
- Reinforces trust with cypherpunk audience

### 7. k-Anonymity Constraint on Analytics — IMPLEMENTING
**What:** Never display analytics for fewer than k=10 distinct user hashes
**How:**
- All admin analytics queries check count(distinct user_hash) >= 10 before returning
- For small counts: show "< 10 users — aggregating for privacy" placeholder
- Implemented in /api/affiliates/metrics endpoint

## NOT IMPLEMENTING (over-engineered for this Flask/SQLite env):
- WebSocket live dashboard → SSE (simpler, same effect, no Redis needed)
- Edge computing / Cloudflare Workers → not applicable to this Flask stack
- Redis for MAB storage → SQLite handles MAB state fine at this scale
- TensorFlow.js behavioral ML → simple scroll/time math is sufficient
- Blockchain referral tracking → misaligned with simplicity requirement
- WebXR experiences → banned by GOSPEL (CSS animations only, no 3D)
- LangChain agent swarms → overkill, Claude Haiku API call is sufficient
- Voice-activated CTAs → novelty without conversion value
