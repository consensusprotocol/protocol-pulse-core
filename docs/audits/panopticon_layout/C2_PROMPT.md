# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: panopticon_layout
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
### Q1 — GRID + PANEL RHYTHM

**Analysis:**
- The gap of `1px` between columns at line 328 is too tight for a 1920px width, leading to a cramped appearance. A wider gutter would help separate the columns visually.
- The panel padding of `20px 16px` at line 345 is insufficient for desktop widths, making the content feel cramped.
- The `max-width` of `1800px` at line 320 limits the layout on ultrawide monitors, causing unused space on the sides.
- The vertical rhythm between columns is inconsistent, leading to visual drift.

**Severity:** HIGH

**Specific Fix:**
- Increase column gap: `gap: clamp(16px, 1.5vw, 28px);`
- Increase panel padding: `padding: clamp(20px, 2vw, 32px);`
- Remove `max-width: 1800px;` to allow full utilization of screen space on ultrawide monitors.
- Ensure consistent vertical alignment by using flexbox or grid alignment properties.

### Q2 — TYPOGRAPHY SCALING

**Analysis:**
- Many text elements use sub-10px font sizes, which are too small for readability on a premium product.
- JetBrains Mono letter-spacing values are too wide at small sizes, reducing readability.

**Severity:** CRITICAL

**Specific Fix:**
- `.pn-hero-stat-label`: `font-size: clamp(10px, 1vw, 12px);`
- `.pn-ticker-tag`: `font-size: clamp(10px, 1vw, 12px);`
- `.pn-panel-head`: `font-size: clamp(12px, 1.2vw, 14px);`
- `.pn-section-label`: `font-size: clamp(12px, 1.2vw, 14px);`
- `#ss2-verdict`: `font-size: clamp(12px, 1.2vw, 14px);`
- `.ss2-wf-label`: `font-size: clamp(10px, 1vw, 12px);`
- `.ss2-wf-contrib`: `font-size: clamp(10px, 1vw, 12px);`
- `.ss2-si-label`: `font-size: clamp(10px, 1vw, 12px);`
- `#ss2-dc-insight`: `font-size: clamp(10px, 1vw, 12px);`
- Reduce letter-spacing for readability: `letter-spacing: clamp(0.1em, 0.2vw, 0.15em);`

### Q3 — HERO STATS BAR

**Analysis:**
- The hero stats bar has adequate min-height and centered alignment at 1920px but may appear small on 2560px.
- The ratio of `.pn-hero-stat-val` 24px to label 9px does not provide a premium feel; the label is too small.
- The radar rings at 600px can be distracting on ultrawide screens.

**Severity:** MEDIUM

**Specific Fix:**
- Increase `.pn-hero-stat-val`: `font-size: clamp(28px, 2.5vw, 32px);`
- Increase `.pn-hero-stat-label`: `font-size: clamp(12px, 1.2vw, 14px);`
- Consider reducing radar ring size or opacity for less distraction on ultrawide screens.

### Q4 — SOVEREIGN SIGNAL SECTION (ss2-root)

**Analysis:**
- `ss2-root` is full-bleed, which can be jarring compared to the rest of the layout.
- The 400px signal board column is too narrow for 1920px and should allow for more content.
- Waterfall bars are cramped at `height: 38px`.
- Gauges row padding is adequate but could use more space for better touch targets.

**Severity:** HIGH

**Specific Fix:**
- Align `ss2-root` with `pn-grid` by setting `max-width: 1800px; margin: 0 auto;`.
- Increase signal board width: `width: clamp(400px, 25vw, 600px);`
- Increase waterfall bar height: `height: clamp(50px, 5vh, 70px);`
- Increase gauge padding: `padding: clamp(16px, 2vw, 24px);`

### Q5 — CARD COMPONENTS

**Analysis:**
- Padding is insufficient for readability and a premium feel.
- Line-height is too tight, affecting readability.
- Border-left accent thickness is inconsistent.
- Max-width constraints are needed to prevent awkward text wraps.

**Severity:** HIGH

**Specific Fix:**
- Increase padding: `padding: clamp(16px, 2vw, 24px);`
- Increase line-height: `line-height: 1.5;`
- Standardize border-left thickness: `border-left: 4px solid;`
- Set max-width for text elements: `max-width: 600px;`

### Q6 — COMMANDER LOCK ON CORRELATION MAP

**Analysis:**
- The proposed approach using Jinja conditional is sound and does not leak Commander data in the DOM.
- The teaser design is on-brand, but ensure axis labels and section headers remain visible.

**Severity:** MEDIUM

**Specific Fix:**
- Implement a blur overlay with CSS: `filter: blur(8px);`
- Ensure axis labels and section header are outside the blurred area.
- Use a centered lock box with a button styled to match the brand palette.

### FINAL VERDICT

**Top 5 CSS changes:**
1. Increase column gap and panel padding for better spacing.
2. Adjust typography to use `clamp()` for better scaling and readability.
3. Align `ss2-root` with `pn-grid` and adjust widths for better consistency.
4. Increase padding and line-height for card components for a premium feel.
5. Implement a consistent approach for the Commander lock on the correlation map.

**What stays as-is:**
- The overall layout structure and component hierarchy are well-defined.
- The use of JetBrains Mono for data and code elements is appropriate and on-brand.

**Overall:** PASS WITH FIXES

## GROK — CYCLE 1 OUTPUT
### PANOPTICON DESKTOP LAYOUT AUDIT

I have conducted a thorough visual design audit of the PANOPTICON dashboard layout for desktop screens (1920x1080+), focusing on the provided CSS and HTML structure. Below are detailed analyses and recommendations for each of the six critical questions, with specific line number citations, severity ratings, and actionable fixes using exact CSS values.

---

### Q1 — GRID + PANEL RHYTHM

**Detailed Analysis:**
- **Gap Tightness (Line 327):** The `.pn-grid` uses a `gap: 1px`, which is excessively tight for a 1920px viewport. At this resolution, a 1px gap is visually imperceptible and fails to provide adequate separation between columns, making the layout feel cramped and cluttered.
- **Panel Padding (Line 346):** The `.pn-panel` padding of `20px 16px` is insufficient for breathing room at desktop widths. At 1920px, this results in content feeling too close to the edges, diminishing the premium feel expected of a high-end dashboard.
- **Max-Width Bottleneck (Line 321):** The `.pn-main` max-width of 1800px is a bottleneck for ultrawide monitors (2560px+). This constraint leaves significant unused space on larger screens, reducing the dashboard's ability to scale gracefully and utilize available real estate.
- **Vertical Rhythm (Lines 325-329):** The three-column grid (`1fr 1.1fr 1fr`) shows inconsistent vertical rhythm due to varying content lengths in each `.pn-panel`. Without a mechanism to balance heights or enforce consistent scrolling behavior, columns visually drift, disrupting the overall harmony.

**Severity:** HIGH
- The tight gap and insufficient padding significantly impact readability and perceived quality on desktop.
- The max-width limitation is a notable issue for ultrawide users, a key demographic for premium dashboards.

**Specific Fix:**
- Update `.pn-grid` gap to `gap: clamp(16px, 1.5vw, 28px);` (Line 327) to ensure visible separation that scales with viewport width.
- Increase `.pn-panel` padding to `padding: clamp(20px, 2vw, 32px) clamp(16px, 1.5vw, 24px);` (Line 346) for better breathing room at desktop resolutions.
- Adjust `.pn-main` max-width to `max-width: clamp(1600px, 90vw, 2400px);` (Line 321) to accommodate ultrawide monitors while maintaining a focused layout.
- Add `display: flex; flex-direction: column; height: calc(100vh - 420px);` to `.pn-panel` (Line 343) and ensure content containers within panels use `flex: 1; overflow-y: auto;` to enforce consistent vertical rhythm by aligning panel heights.

---

### Q2 — TYPOGRAPHY SCALING

**Detailed Analysis:**
- **Hardcoded Small Font Sizes (Multiple Lines):** Numerous elements use sub-10px font sizes, which are below the threshold for comfortable readability on a 1920px desktop display. Examples include:
  - `.pn-hero-stat-label` at 9px (Line 192)
  - `.pn-ticker-tag` at 8px (Line 288)
  - `.pn-panel-head` at 10px (Line 353)
  - `.pn-section-label` at 9px (Line 386)
  - `#ss2-verdict` at 9px (Line 1722)
  - `.ss2-wf-label` at 7px (Line 1992)
  - `.ss2-wf-contrib` at 6.5px (Line 1997)
  - `.ss2-si-label` at 7.5px (Line 1936)
  - `#ss2-dc-insight` at 8.5px (Line 1859)
- These sizes fail to meet the minimum recommended thresholds of ≥10px for labels, ≥12px for values, and ≥14px for headers on a premium product at desktop resolutions. Small text appears pixelated or strained on high-DPI displays, reducing accessibility and perceived quality.
- **Letter-Spacing Readability (Lines 159, 167, 223, 1681, etc.):** JetBrains Mono letter-spacing values range from `.12em` to `.25em` (e.g., `.pn-hero-title` at 12px letter-spacing on Line 159, `.ss2-overline` at .25em on Line 1681). At small font sizes (below 12px), these wide spacings can fragment text, making it harder to read quickly, especially for labels and tickers.

**Severity:** CRITICAL
- Typography is a foundational element of UI design. Sub-10px text at 1920px is a severe accessibility and aesthetic issue, directly impacting user experience on a premium dashboard.

**Specific Fix:**
- Replace hardcoded font sizes with `clamp()` for responsive scaling:
  - `.pn-hero-stat-label` (Line 192): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.pn-ticker-tag` (Line 288): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.pn-panel-head` (Line 353): `font-size: clamp(12px, 0.8vw, 16px);`
  - `.pn-section-label` (Line 386): `font-size: clamp(10px, 0.7vw, 14px);`
  - `#ss2-verdict` (Line 1722): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.ss2-wf-label` (Line 1992): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.ss2-wf-contrib` (Line 1997): `font-size: clamp(9px, 0.5vw, 11px);`
  - `.ss2-si-label` (Line 1936): `font-size: clamp(10px, 0.6vw, 12px);`
  - `#ss2-dc-insight` (Line 1859): `font-size: clamp(10px, 0.6vw, 12px);`
- Adjust letter-spacing for small text to improve readability: For all elements with font sizes potentially below 12px after clamping, set `letter-spacing: clamp(0.08em, 0.1vw, 0.12em);` (e.g., Lines 192, 288, 386). For larger text (headers like `.pn-hero-tit

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PANOPTICON_LAYOUT — CYCLE 1
Generated: 2026-04-15 19:55
Models: gpt4o, grok (+1 failed: gemini — 403 PERMISSION_DENIED: API key reported as leaked)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 — Grid + Panel Rhythm | N/A | HIGH | HIGH | **HIGH** |
| Q2 — Typography Scaling | N/A | CRITICAL | CRITICAL | **CRITICAL** |
| Q3 — Hero Stats Bar | N/A | MEDIUM | MEDIUM | **MEDIUM** |
| Q4 — Sovereign Signal Section | N/A | HIGH | HIGH | **HIGH** |
| Q5 — Card Components | N/A | HIGH | (partial) | **HIGH** |
| Q6 — Commander Lock / Correlation Map | N/A | MEDIUM | (partial) | **MEDIUM** |

> **Scoring note:** Gemini failed with a leaked-key 403 error. All consensus determinations are derived from 2 of 2 available models. Where both agree, confidence is treated as unanimous for this cycle. Gemini must be re-keyed and re-run in Cycle 2 to achieve a full 3-model quorum.

---

## UNANIMOUS FINDINGS (both available models agree — implement unconditionally)

### U1 — Grid gap of `1px` is visually broken at 1920px+
- **What:** `.pn-grid` gap is `1px` (line 327/328), completely invisible at desktop resolutions, making columns appear fused rather than separated.
- **File/Line:** `panopticon_layout.css` line 327–328
- **Change:** `gap: clamp(16px, 1.5vw, 28px);`
- **Confidence:** 2/2 models, both rated HIGH

### U2 — Panel padding `20px 16px` is insufficient at desktop widths
- **What:** `.pn-panel` padding (line 345/346) makes content feel cramped against panel edges, undermining the premium dashboard aesthetic.
- **File/Line:** `panopticon_layout.css` line 345–346
- **Change:** `padding: clamp(20px, 2vw, 32px) clamp(16px, 1.5vw, 24px);`
- **Confidence:** 2/2 models, both rated HIGH

### U3 — Sub-10px font sizes across multiple elements (CRITICAL typography failure)
- **What:** At least 9 distinct elements use font sizes ranging from 6.5px to 9px — below any reasonable readability threshold for a 1920px desktop product. Both models independently enumerated the same elements.
- **File/Line:** Multiple lines across `panopticon_layout.css`
- **Changes (exact):**
  - `.pn-hero-stat-label` (line 192): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.pn-ticker-tag` (line 288): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.pn-panel-head` (line 353): `font-size: clamp(12px, 0.8vw, 16px);`
  - `.pn-section-label` (line 386): `font-size: clamp(10px, 0.7vw, 14px);`
  - `#ss2-verdict` (line 1722): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.ss2-wf-label` (line 1992): `font-size: clamp(10px, 0.6vw, 12px);`
  - `.ss2-wf-contrib` (line 1997): `font-size: clamp(9px, 0.5vw, 11px);`
  - `.ss2-si-label` (line 1936): `font-size: clamp(10px, 0.6vw, 12px);`
  - `#ss2-dc-insight` (line 1859): `font-size: clamp(10px, 0.6vw, 12px);`
- **Confidence:** 2/2 models, both rated CRITICAL

### U4 — JetBrains Mono letter-spacing too wide at small sizes
- **What:** Letter-spacing values of `.12em`–`.25em` on sub-12px text fragment

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: core/blueprints/panopticon.py (540 lines)
```
   1 | """
   2 | PANOPTICON Blueprint — Congressional Disclosure & Whale Intelligence Dashboard
   3 | "They watch us. Now we watch them."
   4 | 
   5 | Routes:
   6 |   /panopticon                          — Main dashboard (Commander-gated)
   7 |   /api/panopticon/disclosures          — STOCK Act filings (crypto-filtered)
   8 |   /api/panopticon/congress             — Alias for disclosures
   9 |   /api/panopticon/whale-alerts         — Whale wallet movements
  10 |   /api/panopticon/whales               — Alias for whale-alerts
  11 |   /api/panopticon/correlations         — Cross-reference timeline
  12 |   /api/panopticon/geopolitical         — Nation-state & macro signals
  13 |   /api/panopticon/polymarket           — Prediction market odds
  14 |   /api/panopticon/make-bitcoin-case    — AI-generated Bitcoin case (POST)
  15 |   /api/panopticon/bitcoin-case         — Alias for make-bitcoin-case
  16 | """
  17 | 
  18 | import logging
  19 | import re
  20 | from flask import Blueprint, render_template, jsonify, request
  21 | from flask_login import current_user
  22 | 
  23 | logger = logging.getLogger(__name__)
  24 | 
  25 | panopticon_bp = Blueprint("panopticon", __name__)
  26 | 
  27 | # ── Rate limiting via app-level Flask-Limiter (P0 audit fix: shared across workers) ──
  28 | # The app.py limiter uses get_remote_address as key_func.
  29 | # We apply limits per-route via a lazy import to avoid circular imports at module load.
  30 | _limiter = None
  31 | 
  32 | 
  33 | def _get_limiter():
  34 |     """Lazy-load the app-level Flask-Limiter instance."""
  35 |     global _limiter
  36 |     if _limiter is None:
  37 |         try:
  38 |             from app import limiter
  39 |             _limiter = limiter
  40 |         except ImportError:
  41 |             try:
  42 |                 from core.app import limiter
  43 |                 _limiter = limiter
  44 |             except ImportError:
  45 |                 logger.warning("Flask-Limiter not available — panopticon rate limiting disabled")
  46 |     return _limiter
  47 | 
  48 | 
  49 | @panopticon_bp.before_request
  50 | def _enforce_rate_limit():
  51 |     """Rate limiting for /api/panopticon/* routes via Flask-Limiter.
  52 |     Falls back to app-level default if limiter unavailable."""
  53 |     if not request.path.startswith("/api/panopticon/"):
  54 |         return None
  55 | 
  56 |     lim = _get_limiter()
  57 |     if lim is None:
  58 |         return None
  59 | 
  60 |     # Flask-Limiter handles enforcement via decorators on individual routes.
  61 |     # This hook exists only for logging/monitoring.
  62 |     return None
  63 | 
  64 | _EMPTY_DATA = {
  65 |     "btc_price": None,
  66 |     "events_today": 0,
  67 |     "disclosures": [],
  68 |     "flagged": [],
  69 |     "whales": [],
  70 |     "forex": [],
  71 |     "geopolitical": [],
  72 |     "correlations": [],
  73 |     "watch_list": [],
  74 |     "polymarket": [],
  75 |     "generated_at": None,
  76 | }
  77 | 
  78 | # Redacted teaser data for free-tier users (no real Commander data leaked)
  79 | _DEMO_DATA = {
  80 |     "btc_price": None,
  81 |     "events_today": 12,
  82 |     "disclosures": [
  83 |         {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
  84 |         {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
  85 |         {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
  86 |     ],
  87 |     "flagged": [
  88 |         {"entity": "██████████", "asset": "CLASSIFIED", "tier": "flagged", "correlation_score": 0.0, "flag_reason": "CLASSIFIED — Upgrade to Commander"},
  89 |     ],
  90 |     "whales": [
  91 |         {"entity": "██████████", "wallet_label": "CLASSIFIED", "address": "████...████", "txid": "████...████", "amount_btc": 0, "tx_type": "classified", "confirmed": True, "timestamp": "████-██-██", "event_type": "whale"},
  92 |     ],
  93 |     "forex": [],
  94 |     "geopolitical": [
  95 |         {"headline": "US Strategic Bitcoin Reserve — Executive Order Establishes National BTC Stockpile", "category": "policy", "btc_signal": "bullish", "btc_rationale": "Nation-state accumulation confirms Bitcoin as strategic reserve asset alongside gold.", "source": "White House", "timestamp": "2025-03-06", "event_type": "geopolitical"},
  96 |         {"headline": "Japan Yen Under Pressure — BOJ Intervention Watch Activated", "category": "macro", "btc_signal": "bullish", "btc_rationale": "Currency debasement historically drives capital to hard assets. BTC +12% avg 30d post yen interventions.", "source": "Reuters", "timestamp": "2026-04-13", "event_type": "geopolitical"},
  97 |         {"headline": "EU MiCA Regulation — Full Crypto Asset Framework Active", "category": "regulation", "btc_signal": "neutral", "btc_rationale": "Regulatory clarity in EU; may push innovation to permissive jurisdictions.", "source": "European Commission", "timestamp": "2025-12-30", "event_type": "geopolitical"},
  98 |         {"headline": "Fed Holds Rates April 2026 — 98.2% Polymarket Probability", "category": "macro", "btc_signal": "bullish", "btc_rationale": "Stable rates remove macro tail risk — historically bullish for Bitcoin.", "source": "Federal Reserve", "timestamp": "2026-04-15", "event_type": "geopolitical"},
  99 |     ],
 100 |     "correlations": [],
 101 |     "watch_list": [],
 102 |     "polymarket": [
 103 |         {"question": "Will there be no change in Fed interest rates after the April 2026 meeting?", "yes_price": 98.2, "volume": 16185557, "volume_24h": 528612, "btc_signal": "bullish", "end_date": "2026-04-29", "source_url": "https://polymarket.com/event/fed-rate-april-2026", "event_type": "prediction"},
 104 |         {"question": "Will Trump acquire Greenland before 2027?", "yes_price": 9.0, "volume": 32493787, "volume_24h": 351955, "btc_signal": "neutral", "end_date": "2026-12-31", "source_url": "https://polymarket.com/event/trump-greenland", "event_type": "prediction"},
 105 |         {"question": "Will the Fed decrease rates by 50+ bps after April 2026?", "yes_price": 0.4, "volume": 26993351, "volume_24h": 1254576, "btc_signal": "bullish", "end_date": "2026-04-29", "source_url": "https://polymarket.com/event/fed-50bps-cut", "event_type": "prediction"},
 106 |         {"question": "Russia x Ukraine ceasefire by end of 2026?", "yes_price": 29.5, "volume": 14068338, "volume_24h": 163912, "btc_signal": "neutral", "end_date": "2026-12-31", "source_url": "https://polymarket.com/event/russia-ukraine-ceasefire-2026", "event_type": "prediction"},
 107 |         {"question": "Will Trump visit China by April 30?", "yes_price": 1.4, "volume": 10568303, "volume_24h": 300536, "btc_signal": "neutral", "end_date": "2026-04-30", "source_url": "https://polymarket.com/event/trump-china-april-2026", "event_type": "prediction"},
 108 |         {"question": "Iran x Israel/US conflict ends by April 15?", "yes_price": 53.4, "volume": 7822474, "volume_24h": 620212, "btc_signal": "neutral", "end_date": "2026-04-15", "source_url": "https://polymarket.com/event/iran-conflict-april-2026", "event_type": "prediction"},
 109 |     ],
 110 |     "generated_at": None,
 111 | }
 112 | 
 113 | 
 114 | def _is_commander() -> bool:
 115 |     """Check if current user has Commander+ tier access."""
 116 |     if not current_user.is_authenticated:
 117 |         return False
 118 |     tier = getattr(current_user, "subscription_tier", "free")
 119 |     return tier in ("commander", "sovereign")
 120 | 
 121 | 
 122 | def _sanitize_event_summary(text: str) -> str:
 123 |     """Sanitize user input for the Make Bitcoin Case prompt to prevent injection.
 124 |     Defense-in-depth layer — primary injection defense is in the system prompt
 125 |     (see panopticon_service.get_make_bitcoin_case)."""
 126 |     # Strip control characters and excessive whitespace
 127 |     text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
 128 |     # Remove common prompt injection patterns
 129 |     text = re.sub(r'(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)', '', text)
 130 |     # Limit to alphanumeric, basic punctuation, and spaces
 131 |     text = re.sub(r'[^\w\s.,;:!?\'"\-()/$%@#&+=]', '', text)
 132 |     return text.strip()[:500]
 133 | 
 134 | 
 135 | def _validate_llm_output(text: str) -> str:
 136 |     """Validate LLM output before rendering to users.
 137 |     P1 audit fix: reject outputs containing instruction-like patterns or code."""
 138 |     if not text:
 139 |         return text
 140 |     # Reject outputs with injection indicators
 141 |     suspicious_patterns = [
 142 |         r'(?i)ignore\s+(all\s+)?previous\s+instructions',
 143 |         r'(?i)system\s*prompt',
 144 |         r'(?i)<script',
 145 |         r'(?i)javascript:',
 146 |         r'(?i)on(load|error|click)\s*=',
 147 |     ]
 148 |     for pattern in suspicious_patterns:
 149 |         if re.search(pattern, text):
 150 |             logger.warning("LLM output validation failed: suspicious pattern detected")
 151 |             return "Self-custody is the only guarantee that no institution can freeze, seize, or debase your savings. Bitcoin is the exit."
 152 |     return text
 153 | 
 154 | 
 155 | # ═══════════════════════════════════════════════════════════════════════════
 156 | # PAGE ROUTE
 157 | # ═══════════════════════════════════════════════════════════════════════════
 158 | 
 159 | @panopticon_bp.route("/panopticon")
 160 | def panopticon_page():
 161 |     """PANOPTICON dashboard — Commander tier sees full data, free tier sees redacted CLASSIFIED data.
 162 |     SECURITY: Free-tier users receive only redacted placeholder data. Real Commander data is NEVER
 163 |     embedded in the HTML payload for unauthenticated or free-tier users."""
 164 |     demo_mode = not _is_commander()
 165 | 
 166 |     if demo_mode:
 167 |         # Free tier: send only redacted demo data — no real data touches the template
 168 |         data = _DEMO_DATA
 169 |     else:
 170 |         # Commander tier: fetch real intelligence data
 171 |         try:
 172 |             from services.panopticon_service import get_dashboard_data
 173 |             data = get_dashboard_data()
 174 |         except Exception as e:
 175 |             logger.error("Panopticon data fetch failed: %s", e)
 176 |             data = _EMPTY_DATA
 177 | 
 178 |     return render_template(
 179 |         "panopticon.html",
 180 |         demo_mode=demo_mode,
 181 |         data=data,
 182 |     )
 183 | 
 184 | 
 185 | # ═══════════════════════════════════════════════════════════════════════════
 186 | # API ROUTES
 187 | # ═══════════════════════════════════════════════════════════════════════════
 188 | 
 189 | @panopticon_bp.route("/api/panopticon/disclosures")
 190 | @panopticon_bp.route("/api/panopticon/congress")
 191 | def api_disclosures():
 192 |     """Recent STOCK Act filings filtered for crypto/fintech."""
 193 |     if not _is_commander():
 194 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 195 | 
 196 |     try:
 197 |         from services.panopticon_service import fetch_disclosures
 198 |         limit = min(int(request.args.get("limit", 50)), 100)
 199 |         disclosures, is_live = fetch_disclosures(limit=limit)
 200 |         return jsonify({
 201 |             "disclosures": disclosures,
 202 |             "count": len(disclosures),
 203 |             "is_live": is_live,
 204 |             "tier": "confirmed",
 205 |         })
 206 |     except Exception as e:
 207 |         logger.error("Disclosures API error: %s", e)
 208 |         return jsonify({"error": "Failed to fetch disclosures"}), 500
 209 | 
 210 | 
 211 | @panopticon_bp.route("/api/panopticon/whale-alerts")
 212 | @panopticon_bp.route("/api/panopticon/whales")
 213 | def api_whale_alerts():
 214 |     """Recent large BTC wallet movements from known entities.
 215 |     Tighter rate limit (10/min) — most expensive upstream call."""
 216 |     if not _is_commander():
 217 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 218 | 
 219 |     try:
 220 |         from services.panopticon_service import fetch_whale_alerts, get_btc_price
 221 |         limit = min(int(request.args.get("limit", 20)), 50)
 222 |         alerts = fetch_whale_alerts(limit=limit)
 223 |         btc_price = get_btc_price()
 224 | 
 225 |         # Enrich with USD
 226 |         if btc_price:
 227 |             for a in alerts:
 228 |                 if a.get("amount_btc"):
 229 |                     a["amount_usd"] = round(a["amount_btc"] * btc_price, 2)
 230 | 
 231 |         return jsonify({
 232 |             "alerts": alerts,
 233 |             "count": len(alerts),
 234 |             "btc_price": btc_price,
 235 |         })
 236 |     except Exception as e:
 237 |         logger.error("Whale alerts API error: %s", e)
 238 |         return jsonify({"error": "Failed to fetch whale alerts"}), 500
 239 | 
 240 | 
 241 | @panopticon_bp.route("/api/panopticon/correlations")
 242 | def api_correlations():
 243 |     """Cross-reference timeline: disclosures x whale movements x geopolitical events."""
 244 |     if not _is_commander():
 245 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 246 | 
 247 |     try:
 248 |         from services.panopticon_service import build_correlations
 249 |         limit = min(int(request.args.get("limit", 10)), 25)
 250 |         correlations = build_correlations(limit=limit)
 251 |         return jsonify({
 252 |             "correlations": correlations,
 253 |             "count": len(correlations),
 254 |         })
 255 |     except Exception as e:
 256 |         logger.error("Correlations API error: %s", e)
 257 |         return jsonify({"error": "Failed to build correlations"}), 500
 258 | 
 259 | 
 260 | @panopticon_bp.route("/api/panopticon/geopolitical")
 261 | def api_geopolitical():
 262 |     """Nation-state signals, forex interventions, sovereign BTC activity."""
 263 |     if not _is_commander():
 264 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 265 | 
 266 |     try:
 267 |         from services.panopticon_service import fetch_geopolitical, fetch_forex_signals
 268 |         geo = fetch_geopolitical()
 269 |         forex = fetch_forex_signals()
 270 |         return jsonify({
 271 |             "geopolitical": geo,
 272 |             "forex": forex,
 273 |             "count": len(geo) + len(forex),
 274 |         })
 275 |     except Exception as e:
 276 |         logger.error("Geopolitical API error: %s", e)
 277 |         return jsonify({"error": "Failed to fetch geopolitical signals"}), 500
 278 | 
 279 | 
 280 | 
 281 | 
 282 | # ═══════════════════════════════════════════════════════════════════════════
 283 | # PRIVATE EQUITY & INSTITUTIONAL INTELLIGENCE (SEC EDGAR)
 284 | # ═══════════════════════════════════════════════════════════════════════════
 285 | 
 286 | @panopticon_bp.route("/api/panopticon/institutional")
 287 | def api_institutional():
 288 |     """SEC EDGAR 13F institutional Bitcoin ETF holdings.
 289 |     Public: entity names + institution type. Commander: full detail with shares/values."""
 290 |     try:
 291 |         import importlib.util as _ilu
 292 |         _s = _ilu.spec_from_file_location('edgar_service',
 293 |             '/home/ultron/protocol_pulse/services/edgar_service.py')
 294 |         _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
 295 |         institutional = _m.fetch_institutional_btc_13f(20)
 296 |         coalition = [f for f in institutional if f.get("coalition_detected")]
 297 | 
 298 |         def _public_inst(r):
 299 |             return {
 300 |                 "entity": r.get("entity", ""),
 301 |                 "institution_type": r.get("institution_type", ""),
 302 |                 "filing_date": r.get("filing_date", ""),
 303 |                 "ticker": r.get("ticker", ""),
 304 |                 "coalition_detected": r.get("coalition_detected", False),
 305 |                 "coalition_score": r.get("coalition_score", 0),
 306 |             }
 307 | 
 308 |         is_cmd = _is_commander()
 309 |         return jsonify({
 310 |             "institutional_13f": institutional if is_cmd else [_public_inst(f) for f in institutional[:8]],
 311 |             "total_institutional_filers": len(institutional),
 312 |             "coalition_summary": {
 313 |                 "detected": bool(coalition),
 314 |                 "count": len(coalition),
 315 |                 "active_months": {}
 316 |             },
 317 |             "commander_only": not is_cmd,
 318 |             "source": "SEC EDGAR (Free Public API)",
 319 |         })
 320 |     except Exception as e:
 321 |         logger.error("EDGAR institutional data failed: %s", e)
 322 |         return jsonify({"error": str(e), "institutional_13f": [], "total_institutional_filers": 0}), 500
 323 | 
 324 | 
 325 | @panopticon_bp.route("/api/panopticon/pe-datastream")
 326 | def api_pe_datastream():
 327 |     """Private equity datastream: Form D fundraising + coalition analysis.
 328 |     Public: counts + entity names only. Commander: full detail with amounts."""
 329 |     try:
 330 |         import importlib.util as _ilu
 331 |         _s = _ilu.spec_from_file_location('edgar_service',
 332 |             '/home/ultron/protocol_pulse/services/edgar_service.py')
 333 |         _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
 334 |         fetch_pe_fundraising_btc = _m.fetch_pe_fundraising_btc
 335 |         fetch_institutional_btc_13f = _m.fetch_institutional_btc_13f
 336 |         import datetime as _dt
 337 |         pe_rounds = fetch_pe_fundraising_btc(30)
 338 |         institutional = fetch_institutional_btc_13f(20)
 339 |         coalition = [f for f in institutional if f.get("coalition_detected")]
 340 |         # Strip amounts for public view, full detail for Commander
 341 |         def _public_round(r):
 342 |             return {"entity": r.get("entity",""), "form": r.get("form",""),
 343 |                     "filing_date": r.get("filing_date",""), "sector": r.get("sector","")}
 344 |         def _public_inst(r):
 345 |             return {"entity": r.get("entity",""), "institution_type": r.get("institution_type",""),
 346 |                     "filing_date": r.get("filing_date",""), "ticker": r.get("ticker","")}
 347 | 
 348 |         is_cmd = _is_commander()
 349 |         return jsonify({
 350 |             "pe_rounds": pe_rounds if is_cmd else [_public_round(r) for r in pe_rounds[:5]],
 351 |             "pe_count": len(pe_rounds),
 352 |             "institutional_13f": institutional if is_cmd else [_public_inst(r) for r in institutional[:5]],
 353 |             "coalition_signals": coalition if is_cmd else [],
 354 |             "coalition_count": len(coalition),
 355 |             "coalition_active": bool(coalition),
 356 |             "insight": (
 357 |                 "COALITION SIGNAL: {} institutions accumulated BTC ETFs "
 358 |                 "in coordinated windows.".format(len(coalition))
 359 |                 if coalition else "No coalition pattern detected."
 360 |             ),
 361 |             "commander_only": not is_cmd,
 362 |             "source": "SEC EDGAR (Free Public API)",
 363 |             "updated_at": _dt.datetime.now().isoformat(),
 364 |         })
 365 |     except Exception as e:
 366 |         logger.error("PE datastream failed: %s", e)
 367 |         return jsonify({"error": str(e), "pe_rounds": []}), 500
 368 | 
 369 | 
 370 | @panopticon_bp.route("/api/panopticon/polymarket")
 371 | def api_polymarket():
 372 |     """Live Polymarket prediction market odds for crypto/macro events."""
 373 |     if not _is_commander():
 374 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 375 | 
 376 |     try:
 377 |         from services.panopticon_service import fetch_polymarket_markets
 378 |         limit = min(int(request.args.get("limit", 15)), 30)
 379 |         markets = fetch_polymarket_markets(limit=limit)
 380 |         return jsonify({
 381 |             "markets": markets,
 382 |             "count": len(markets),
 383 |         })
 384 |     except Exception as e:
 385 |         logger.error("Polymarket API error: %s", e)
 386 |         return jsonify({"error": "Failed to fetch Polymarket data"}), 500
 387 | 
 388 | 
 389 | @panopticon_bp.route("/api/panopticon/make-bitcoin-case", methods=["POST"])
 390 | @panopticon_bp.route("/api/panopticon/bitcoin-case", methods=["POST"])
 391 | def api_make_bitcoin_case():
 392 |     """Generate a cypherpunk Bitcoin self-custody argument for a specific event via Claude."""
 393 |     if not _is_commander():
 394 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 395 | 
 396 |     try:
 397 |         body = request.get_json(silent=True) or {}
 398 |         raw_summary = body.get("event_summary", "").strip()
 399 |         if not raw_summary:
 400 |             return jsonify({"error": "event_summary is required"}), 400
 401 |         event_summary = _sanitize_event_summary(raw_summary)
 402 |         if not event_summary:
 403 |             return jsonify({"error": "event_summary contains no valid content"}), 400
 404 | 
 405 |         from services.panopticon_service import get_make_bitcoin_case
 406 |         result = get_make_bitcoin_case(event_summary)
 407 |         # P1 audit fix: validate LLM output before rendering to users
 408 |         if result.get("case_text"):
 409 |             result["case_text"] = _validate_llm_output(result["case_text"])
 410 |         return jsonify(result)
 411 |     except Exception as e:
 412 |         logger.error("Make Bitcoin Case API error: %s", e)
 413 |         return jsonify({"error": "Failed to generate Bitcoin case"}), 500
 414 | 
 415 | 
 416 | 
 417 | @panopticon_bp.route('/api/panopticon/stream')
 418 | def api_panopticon_stream():
 419 |     # SSE real-time: orb every 30s, whale every 2min, congress every 5min
 420 |     import time, json as _j
 421 |     from pathlib import Path
 422 |     from flask import Response, stream_with_context
 423 |     from datetime import datetime, timezone
 424 |     def _sig():
 425 |         try: return _j.loads(Path('/home/ultron/protocol_pulse/data/signals.json').read_text())
 426 |         except: return {}
 427 |     def _sent():
 428 |         p = Path('/tmp/sentinel_state.json')
 429 |         try: return _j.loads(p.read_text()) if p.exists() else {}
 430 |         except: return {}
 431 |     def generate():
 432 |         tick = 0
 433 |         sig = _sig(); sent = _sent()
 434 |         def orb_evt(s, sn):
 435 |             return _j.dumps({'type':'orb_update','ts':datetime.now(timezone.utc).isoformat(),
 436 |                 'btc':{'price':s.get('btc_price',{}).get('value',0),'change_24h':s.get('btc_price',{}).get('change_24h',0)},
 437 |                 'fear_greed':s.get('fear_greed',{}),'hashrate':s.get('hashrate',{}).get('value',''),
 438 |                 'dominance':s.get('dominance',{}).get('value',0),'signal_score':s.get('signal_score',{}),
 439 |                 'convergence':{'state':sn.get('convergence_state','IDLE'),'patterns':sn.get('active_patterns',[])}})
 440 |         yield 'data: ' + _j.dumps({'type':'connected','ts':datetime.now(timezone.utc).isoformat()}) + '\n\n'
 441 |         yield 'data: ' + orb_evt(sig, sent) + '\n\n'
 442 |         while True:
 443 |             try:
 444 |                 time.sleep(15); tick += 1
 445 |                 yield 'data: ' + _j.dumps({'type':'heartbeat','tick':tick}) + '\n\n'
 446 |                 if tick % 2 == 0:
 447 |                     sig = _sig(); sent = _sent()
 448 |                     yield 'data: ' + orb_evt(sig, sent) + '\n\n'
 449 |                 if tick % 8 == 0:
 450 |                     try:
 451 |                         from services.panopticon_service import fetch_whale_alerts
 452 |                         a = fetch_whale_alerts(limit=8)
 453 |                         yield 'data: ' + _j.dumps({'type':'whale_update','alerts':a,'count':len(a)}) + '\n\n'
 454 |                     except: pass
 455 |                 if tick % 20 == 0:
 456 |                     try:
 457 |                         from services.congress_trading_service import CongressTradingService
 458 |                         svc = CongressTradingService()
 459 |                         yield 'data: ' + _j.dumps({'type':'congress_update','ihx':svc.get_insider_heat_score(),'trades':svc.get_recent_trades(8)}) + '\n\n'
 460 |                     except: pass
 461 |                 if tick % 60 == 0:
 462 |                     try:
 463 |                         import sys as _s; _s.path.insert(0, '/home/ultron/protocol_pulse')
 464 |                         from services.perception_layer import fetch_all as _pfa
 465 |                         pd = _pfa()
 466 |                         yield 'data: ' + _j.dumps({'type':'perception_update','composite':pd['composite'],'fee_market':pd.get('fee_market',{}),'lightning':pd.get('lightning_health',{}),'trending':pd.get('trending_narratives',{}).get('active_narratives',[]),'social_velocity':pd.get('social_sentiment',{}).get('velocity_label',''),'fg_trend':pd.get('fg_trend',{})}) + '\n\n'
 467 |                     except: pass
 468 |             except GeneratorExit: return
 469 |             except Exception as ex: logger.warning('SSE error: %s', ex); time.sleep(5)
 470 |     return Response(stream_with_context(generate()), mimetype='text/event-stream',
 471 |         headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
 472 | 
 473 | 
 474 | @panopticon_bp.route('/api/panopticon/perception')
 475 | def api_perception_layer():
 476 |     # Perception Layer: social sentiment, narrative velocity, on-chain fundamentals
 477 |     # Public endpoint - no auth required (score visible, full detail for Commander)
 478 |     try:
 479 |         import importlib.util as _ilu
 480 |         _spec = _ilu.spec_from_file_location('perception_layer',
 481 |             '/home/ultron/protocol_pulse/services/perception_layer.py')
 482 |         _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
 483 |         data = _mod.fetch_all()
 484 |         if _is_commander():
 485 |             return jsonify(data)
 486 |         # Free tier: composite score only
 487 |         return jsonify({
 488 |             'perception_score': data['composite']['perception_score'],
 489 |             'label': data['composite']['label'],
 490 |             'overall_signal': data['composite']['overall_signal'],
 491 |             'updated_at': data['updated_at'],
 492 |             'upgrade': 'Upgrade to Commander for full intelligence breakdown',
 493 |         })
 494 |     except Exception as e:
 495 |         logger.error('Perception Layer API error: %s', e)
 496 |         return jsonify({'error': str(e)}), 500
 497 | 
 498 | 
 499 | 
 500 | 
 501 | @panopticon_bp.route('/api/panopticon/bills')
 502 | def api_bills():
 503 |     # Bitcoin Bill Gap Tracker - public endpoint
 504 |     try:
 505 |         import importlib.util as _ilu
 506 |         _spec = _ilu.spec_from_file_location('bill_tracker',
 507 |             '/home/ultron/protocol_pulse/services/bill_tracker.py')
 508 |         _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
 509 |         data = _mod.fetch_all_bills()
 510 |         # Filter to Bitcoin-relevant bills only for public view
 511 |         btc_bills = [b for b in data.get('bills',[]) if
 512 |             any(c in b.get('categories',[]) for c in
 513 |                 ['strategic_reserve','stablecoin','cbdc','market_structure','self_custody','mining','taxation'])]
 514 |         data['bills'] = btc_bills[:20]
 515 |         data['total_bills'] = len(btc_bills)
 516 |         return jsonify(data)
 517 |     except Exception as e:
 518 |         logger.error('Bill tracker API error: %s', e)
 519 |         return jsonify({'error': str(e), 'bills': []}), 500
 520 | 
 521 | 
 522 | @panopticon_bp.route('/api/panopticon/bills/vote', methods=['POST'])
 523 | def api_bills_vote():
 524 |     # Record a public vote on a bill
 525 |     d = request.get_json(silent=True) or {}
 526 |     bill_id = d.get('bill_id')
 527 |     bill_number = d.get('bill_number', '')
 528 |     vote = d.get('vote', '').lower()
 529 |     if not bill_id or vote not in ('yes', 'no'):
 530 |         return jsonify({'error': 'bill_id and vote (yes/no) required'}), 400
 531 |     try:
 532 |         import importlib.util as _ilu
 533 |         _spec = _ilu.spec_from_file_location('bill_tracker',
 534 |             '/home/ultron/protocol_pulse/services/bill_tracker.py')
 535 |         _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
 536 |         result = _mod.cast_public_vote(int(bill_id), bill_number, vote)
 537 |         return jsonify({'success': True, 'votes': result})
 538 |     except Exception as e:
 539 |         return jsonify({'error': str(e)}), 500
 540 | 
```

### File: templates/panopticon.html (3703 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}PANOPTICON — Congressional Intelligence | Protocol Pulse
   4 | <script src="/static/js/panopticon_stream.js"></script>
   5 | {% endblock %}
   6 | {% block meta_description %}Real-time intelligence dashboard tracking congressional disclosures, whale wallet movements, and geopolitical financial signals cross-referenced with Bitcoin data.{% endblock %}
   7 | 
   8 | {% block head %}
   9 | <link rel="preconnect" href="https://fonts.googleapis.com">
  10 | <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  11 | <style>
  12 | /* ═══════════════════════════════════════════════════════════════════════
  13 |    PANOPTICON — "They watch us. Now we watch them."
  14 |    Surveillance Grid × Bloomberg Terminal
  15 |    ═══════════════════════════════════════════════════════════════════════ */
  16 | :root {
  17 |     --pn-bg: #000;
  18 |     --pn-surface: #0a0a0a;
  19 |     --pn-surface-2: #111;
  20 |     --pn-border: #1a1a1a;
  21 |     --pn-border-active: #333;
  22 |     --pn-text: #fff;
  23 |     --pn-text-secondary: #888;
  24 |     --pn-muted: #555;
  25 |     --pn-red: #ff3b5f;
  26 |     --pn-red-dim: rgba(255,59,95,0.12);
  27 |     --pn-gold: #f8c15c;
  28 |     --pn-white: #fff;
  29 | }
  30 | 
  31 | * { box-sizing: border-box; }
  32 | 
  33 | body.panopticon-body {
  34 |     background: var(--pn-bg) !important;
  35 |     color: var(--pn-text);
  36 |     font-family: 'Inter', -apple-system, sans-serif;
  37 |     margin: 0;
  38 |     padding: 0;
  39 |     overflow-x: hidden;
  40 |     -webkit-font-smoothing: antialiased;
  41 | }
  42 | body.panopticon-body nav,
  43 | body.panopticon-body .navbar,
  44 | body.panopticon-body footer,
  45 | body.panopticon-body .site-footer,
  46 | body.panopticon-body .pp-nav,
  47 | body.panopticon-body .pp-footer { display: none !important; }
  48 | 
  49 | /* ── HERO SECTION — RADAR SWEEP ─────────────────────────────── */
  50 | .pn-hero {
  51 |     position: relative;
  52 |     width: 100%;
  53 |     height: 340px;
  54 |     overflow: hidden;
  55 |     display: flex;
  56 |     align-items: center;
  57 |     justify-content: center;
  58 |     flex-direction: column;
  59 |     border-bottom: 1px solid var(--pn-border);
  60 | }
  61 | .pn-hero-radar {
  62 |     position: absolute;
  63 |     inset: 0;
  64 |     overflow: hidden;
  65 | }
  66 | /* Radar concentric rings */
  67 | .pn-radar-rings {
  68 |     position: absolute;
  69 |     top: 50%;
  70 |     left: 50%;
  71 |     width: 600px;
  72 |     height: 600px;
  73 |     transform: translate(-50%, -50%);
  74 | }
  75 | .pn-radar-ring {
  76 |     position: absolute;
  77 |     top: 50%;
  78 |     left: 50%;
  79 |     border: 1px solid rgba(255,59,95,0.06);
  80 |     border-radius: 50%;
  81 | }
  82 | .pn-radar-ring:nth-child(1) { width: 150px; height: 150px; transform: translate(-50%,-50%); }
  83 | .pn-radar-ring:nth-child(2) { width: 300px; height: 300px; transform: translate(-50%,-50%); }
  84 | .pn-radar-ring:nth-child(3) { width: 450px; height: 450px; transform: translate(-50%,-50%); }
  85 | .pn-radar-ring:nth-child(4) { width: 600px; height: 600px; transform: translate(-50%,-50%); }
  86 | /* Crosshairs */
  87 | .pn-radar-cross {
  88 |     position: absolute;
  89 |     top: 50%;
  90 |     left: 50%;
  91 |     width: 600px;
  92 |     height: 600px;
  93 |     transform: translate(-50%,-50%);
  94 | }
  95 | .pn-radar-cross::before,
  96 | .pn-radar-cross::after {
  97 |     content: '';
  98 |     position: absolute;
  99 |     background: rgba(255,59,95,0.04);
 100 | }
 101 | .pn-radar-cross::before {
 102 |     top: 0;
 103 |     left: 50%;
 104 |     width: 1px;
 105 |     height: 100%;
 106 | }
 107 | .pn-radar-cross::after {
 108 |     top: 50%;
 109 |     left: 0;
 110 |     width: 100%;
 111 |     height: 1px;
 112 | }
 113 | /* Rotating sweep beam */
 114 | .pn-radar-sweep {
 115 |     position: absolute;
 116 |     top: 50%;
 117 |     left: 50%;
 118 |     width: 300px;
 119 |     height: 300px;
 120 |     transform-origin: 0 0;
 121 |     animation: radarSweep 6s linear infinite;
 122 |     background: conic-gradient(
 123 |         from 0deg,
 124 |         transparent 0deg,
 125 |         rgba(255,59,95,0.15) 10deg,
 126 |         rgba(255,59,95,0.08) 30deg,
 127 |         transparent 60deg
 128 |     );
 129 |     border-radius: 0 300px 0 0;
 130 |     pointer-events: none;
 131 | }
 132 | @keyframes radarSweep {
 133 |     from { transform: rotate(0deg); }
 134 |     to { transform: rotate(360deg); }
 135 | }
 136 | /* Scan lines */
 137 | .pn-scanlines {
 138 |     position: absolute;
 139 |     inset: 0;
 140 |     background: repeating-linear-gradient(
 141 |         to bottom,
 142 |         transparent 0px,
 143 |         transparent 2px,
 144 |         rgba(255,59,95,0.015) 2px,
 145 |         rgba(255,59,95,0.015) 4px
 146 |     );
 147 |     pointer-events: none;
 148 | }
 149 | /* Hero content */
 150 | .pn-hero-content {
 151 |     position: relative;
 152 |     z-index: 2;
 153 |     text-align: center;
 154 | }
 155 | .pn-hero-title {
 156 |     font-family: 'JetBrains Mono', monospace;
 157 |     font-weight: 800;
 158 |     font-size: 42px;
 159 |     letter-spacing: 12px;
 160 |     text-transform: uppercase;
 161 |     color: var(--pn-red);
 162 |     margin: 0 0 8px;
 163 |     text-shadow: 0 0 40px rgba(255,59,95,0.3);
 164 | }
 165 | .pn-hero-tagline {
 166 |     font-family: 'JetBrains Mono', monospace;
 167 |     font-size: 13px;
 168 |     letter-spacing: 6px;
 169 |     text-transform: uppercase;
 170 |     color: var(--pn-text-secondary);
 171 |     margin: 0 0 24px;
 172 | }
 173 | .pn-hero-stats {
 174 |     display: flex;
 175 |     gap: 32px;
 176 |     justify-content: center;
 177 |     align-items: center;
 178 | }
 179 | .pn-hero-stat {
 180 |     text-align: center;
 181 | }
 182 | .pn-hero-stat-val {
 183 |     font-family: 'JetBrains Mono', monospace;
 184 |     font-size: 24px;
 185 |     font-weight: 700;
 186 |     color: var(--pn-white);
 187 | }
 188 | .pn-hero-stat-label {
 189 |     font-family: 'JetBrains Mono', monospace;
 190 |     font-size: 9px;
 191 |     letter-spacing: 2px;
 192 |     text-transform: uppercase;
 193 |     color: var(--pn-muted);
 194 |     margin-top: 4px;
 195 | }
 196 | .pn-hero-stat-sep {
 197 |     width: 1px;
 198 |     height: 32px;
 199 |     background: var(--pn-border);
 200 | }
 201 | /* Header bar */
 202 | .pn-topbar {
 203 |     position: sticky;
 204 |     top: 0;
 205 |     z-index: 100;
 206 |     display: flex;
 207 |     align-items: center;
 208 |     justify-content: space-between;
 209 |     padding: 8px 16px;
 210 |     background: rgba(0,0,0,0.92);
 211 |     backdrop-filter: blur(12px);
 212 |     -webkit-backdrop-filter: blur(12px);
 213 |     border-bottom: 1px solid var(--pn-border);
 214 | }
 215 | .pn-topbar-left {
 216 |     display: flex;
 217 |     align-items: center;
 218 |     gap: 16px;
 219 | }
 220 | .pn-topbar-logo {
 221 |     font-family: 'JetBrains Mono', monospace;
 222 |     font-weight: 800;
 223 |     font-size: 12px;
 224 |     letter-spacing: 3px;
 225 |     color: var(--pn-red);
 226 | }
 227 | .pn-topbar-status {
 228 |     display: flex;
 229 |     align-items: center;
 230 |     gap: 6px;
 231 |     font-family: 'JetBrains Mono', monospace;
 232 |     font-size: 10px;
 233 |     color: var(--pn-red);
 234 |     letter-spacing: 1px;
 235 | }
 236 | .pn-topbar-dot {
 237 |     width: 6px;
 238 |     height: 6px;
 239 |     border-radius: 50%;
 240 |     background: var(--pn-red);
 241 |     animation: pnPulse 2s ease-in-out infinite;
 242 | }
 243 | @keyframes pnPulse {
 244 |     0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(255,59,95,0.5); }
 245 |     50% { opacity: 0.4; box-shadow: 0 0 0 4px rgba(255,59,95,0); }
 246 | }
 247 | .pn-topbar-right {
 248 |     display: flex;
 249 |     align-items: center;
 250 |     gap: 20px;
 251 | }
 252 | .pn-topbar-clock {
 253 |     font-family: 'JetBrains Mono', monospace;
 254 |     font-size: 13px;
 255 |     font-weight: 500;
 256 |     color: var(--pn-white);
 257 |     letter-spacing: 1px;
 258 | }
 259 | .pn-topbar-btc {
 260 |     font-family: 'JetBrains Mono', monospace;
 261 |     font-size: 13px;
 262 |     font-weight: 700;
 263 |     color: var(--pn-gold);
 264 | }
 265 | .pn-topbar-back {
 266 |     color: var(--pn-muted);
 267 |     text-decoration: none;
 268 |     font-family: 'JetBrains Mono', monospace;
 269 |     font-size: 10px;
 270 |     letter-spacing: 1px;
 271 |     transition: color 0.2s;
 272 | }
 273 | .pn-topbar-back:hover { color: var(--pn-white); }
 274 | 
 275 | /* ── LIVE TICKER ─────────────────────────────────────────────── */
 276 | .pn-ticker {
 277 |     display: flex;
 278 |     align-items: center;
 279 |     padding: 6px 16px;
 280 |     border-bottom: 1px solid var(--pn-border);
 281 |     background: var(--pn-surface);
 282 |     gap: 12px;
 283 |     overflow: hidden;
 284 |     min-height: 32px;
 285 | }
 286 | .pn-ticker-tag {
 287 |     font-family: 'JetBrains Mono', monospace;
 288 |     font-size: 8px;
 289 |     font-weight: 800;
 290 |     letter-spacing: 2px;
 291 |     text-transform: uppercase;
 292 |     color: var(--pn-red);
 293 |     padding: 2px 8px;
 294 |     border: 1px solid rgba(255,59,95,0.3);
 295 |     background: rgba(255,59,95,0.06);
 296 |     white-space: nowrap;
 297 |     flex-shrink: 0;
 298 | }
 299 | .pn-ticker-scroll {
 300 |     flex: 1;
 301 |     overflow: hidden;
 302 |     position: relative;
 303 |     height: 16px;
 304 | }
 305 | .pn-ticker-text {
 306 |     font-family: 'JetBrains Mono', monospace;
 307 |     font-size: 10px;
 308 |     color: var(--pn-text-secondary);
 309 |     white-space: nowrap;
 310 |     position: absolute;
 311 |     animation: tickerScroll 40s linear infinite;
 312 | }
 313 | @keyframes tickerScroll {
 314 |     0% { transform: translateX(0); }
 315 |     100% { transform: translateX(-50%); }
 316 | }
 317 | 
 318 | /* ── MAIN GRID ───────────────────────────────────────────────── */
 319 | .pn-main {
 320 |     max-width: 1800px;
 321 |     margin: 0 auto;
 322 |     padding: 0;
 323 | }
 324 | .pn-grid {
 325 |     display: grid;
 326 |     grid-template-columns: 1fr 1.1fr 1fr;
 327 |     gap: 1px;
 328 |     background: var(--pn-border);
 329 |     min-height: calc(100vh - 420px);
 330 | }
 331 | @media (max-width: 1200px) {
 332 |     .pn-grid { grid-template-columns: 1fr 1fr; }
 333 | }
 334 | @media (max-width: 768px) {
 335 |     .pn-grid { grid-template-columns: 1fr; }
 336 |     .pn-hero { height: 240px; }
 337 |     .pn-hero-title { font-size: 24px; letter-spacing: 6px; }
 338 |     .pn-hero-stats { flex-wrap: wrap; gap: 16px; }
 339 |     .pn-hero-stat-val { font-size: 18px; }
 340 | }
 341 | 
 342 | /* ── PANEL ────────────────────────────────────────────────────── */
 343 | .pn-panel {
 344 |     background: var(--pn-bg);
 345 |     padding: 20px 16px;
 346 |     position: relative;
 347 |     overflow-y: auto;
 348 |     max-height: calc(100vh - 200px);
 349 | }
 350 | .pn-panel-head {
 351 |     font-family: 'JetBrains Mono', monospace;
 352 |     font-size: 10px;
 353 |     font-weight: 700;
 354 |     text-transform: uppercase;
 355 |     letter-spacing: 2px;
 356 |     margin-bottom: 16px;
 357 |     padding-bottom: 10px;
 358 |     border-bottom: 1px solid var(--pn-border);
 359 |     display: flex;
 360 |     align-items: center;
 361 |     gap: 10px;
 362 | }
 363 | .pn-panel-head .tier-dot {
 364 |     width: 6px;
 365 |     height: 6px;
 366 |     border-radius: 50%;
 367 |     flex-shrink: 0;
 368 | }
 369 | .pn-panel-head .tier-label {
 370 |     flex: 1;
 371 | }
 372 | .pn-panel-head .tier-count {
 373 |     font-size: 9px;
 374 |     color: var(--pn-muted);
 375 |     font-weight: 500;
 376 | }
 377 | .pn-tier-confirmed .tier-dot { background: var(--pn-red); box-shadow: 0 0 8px rgba(255,59,95,0.4); }
 378 | .pn-tier-confirmed .pn-panel-head { color: var(--pn-red); }
 379 | .pn-tier-flagged .tier-dot { background: var(--pn-gold); box-shadow: 0 0 8px rgba(248,193,92,0.4); }
 380 | .pn-tier-flagged .pn-panel-head { color: var(--pn-gold); }
 381 | .pn-tier-feed .tier-dot { background: var(--pn-white); box-shadow: 0 0 8px rgba(255,255,255,0.3); }
 382 | .pn-tier-feed .pn-panel-head { color: var(--pn-white); }
 383 | 
 384 | .pn-section-label {
 385 |     font-family: 'JetBrains Mono', monospace;
 386 |     font-size: 9px;
 387 |     font-weight: 700;
 388 |     letter-spacing: 2px;
 389 |     text-transform: uppercase;
 390 |     color: var(--pn-muted);
 391 |     margin: 20px 0 10px;
 392 |     padding-top: 12px;
 393 |     border-top: 1px solid var(--pn-border);
 394 | }
 395 | 
 396 | /* ── DISCLOSURE CARDS ─────────────────────────────────────────── */
 397 | .pn-disc-card {
 398 |     background: var(--pn-surface);
 399 |     border: 1px solid var(--pn-border);
 400 |     border-left: 3px solid var(--pn-red);
 401 |     padding: 14px;
 402 |     margin-bottom: 8px;
 403 |     transition: border-color 0.3s, transform 0.3s;
 404 |     opacity: 0;
 405 |     transform: translateX(-8px);
 406 |     animation: cardEnter 0.4s ease forwards;
 407 | }
 408 | .pn-disc-card:nth-child(1) { animation-delay: 0.1s; }
 409 | .pn-disc-card:nth-child(2) { animation-delay: 0.2s; }
 410 | .pn-disc-card:nth-child(3) { animation-delay: 0.3s; }
 411 | .pn-disc-card:nth-child(4) { animation-delay: 0.4s; }
 412 | .pn-disc-card:nth-child(5) { animation-delay: 0.5s; }
 413 | @keyframes cardEnter {
 414 |     to { opacity: 1; transform: translateX(0); }
 415 | }
 416 | .pn-disc-card:hover { border-color: var(--pn-red); }
 417 | .pn-disc-head {
 418 |     display: flex;
 419 |     justify-content: space-between;
 420 |     align-items: center;
 421 |     margin-bottom: 10px;
 422 | }
 423 | .pn-disc-entity {
 424 |     font-size: 14px;
 425 |     font-weight: 600;
 426 |     color: var(--pn-white);
 427 |     overflow: hidden;
 428 |     white-space: nowrap;
 429 | }
 430 | /* Typewriter effect for entity names */
 431 | .pn-disc-entity.typewriter {
 432 |     border-right: 2px solid var(--pn-red);
 433 |     animation: typewriterBlink 0.7s step-end infinite;
 434 |     width: 0;
 435 |     display: inline-block;
 436 | }
 437 | @keyframes typewriterBlink {
 438 |     50% { border-color: transparent; }
 439 | }
 440 | .pn-disc-party {
 441 |     font-family: 'JetBrains Mono', monospace;
 442 |     font-size: 9px;
 443 |     font-weight: 700;
 444 |     padding: 2px 8px;
 445 |     letter-spacing: 1px;
 446 |     flex-shrink: 0;
 447 | }
 448 | .pn-disc-party.R { background: rgba(255,59,95,0.15); color: var(--pn-red); }
 449 | .pn-disc-party.D { background: rgba(255,255,255,0.08); color: var(--pn-white); }
 450 | .pn-disc-party.I { background: rgba(255,255,255,0.05); color: var(--pn-muted); }
 451 | .pn-disc-fields {
 452 |     display: grid;
 453 |     grid-template-columns: 1fr 1fr;
 454 |     gap: 6px;
 455 | }
 456 | .pn-disc-field-label {
 457 |     font-family: 'JetBrains Mono', monospace;
 458 |     font-size: 8px;
 459 |     font-weight: 700;
 460 |     letter-spacing: 1.5px;
 461 |     text-transform: uppercase;
 462 |     color: var(--pn-muted);
 463 | }
 464 | .pn-disc-field-val {
 465 |     font-family: 'JetBrains Mono', monospace;
 466 |     font-size: 12px;
 467 |     font-weight: 500;
 468 |     color: var(--pn-white);
 469 | }
 470 | .pn-disc-field-val.buy { color: #89ffb8; }
 471 | .pn-disc-field-val.sell { color: var(--pn-red); }
 472 | .pn-disc-correlation {
 473 |     margin-top: 10px;
 474 |     padding: 8px 10px;
 475 |     background: rgba(255,59,95,0.04);
 476 |     border: 1px solid rgba(255,59,95,0.12);
 477 |     font-family: 'JetBrains Mono', monospace;
 478 |     font-size: 10px;
 479 |     color: var(--pn-red);
 480 |     line-height: 1.4;
 481 |     position: relative;
 482 |     overflow: hidden;
 483 | }
 484 | .pn-disc-correlation::before {
 485 |     content: "PATTERN DETECTED";
 486 |     display: block;
 487 |     font-size: 8px;
 488 |     font-weight: 800;
 489 |     letter-spacing: 2px;
 490 |     margin-bottom: 4px;
 491 |     opacity: 0.7;
 492 | }
 493 | /* Red ripple pulse on PATTERN DETECTED */
 494 | .pn-disc-correlation::after {
 495 |     content: '';
 496 |     position: absolute;
 497 |     top: 50%;
 498 |     left: 50%;
 499 |     width: 200%;
 500 |     height: 200%;
 501 |     transform: translate(-50%,-50%) scale(0);
 502 |     background: radial-gradient(circle, rgba(255,59,95,0.08) 0%, transparent 70%);
 503 |     animation: patternPulse 3s ease-out infinite;
 504 |     pointer-events: none;
 505 | }
 506 | @keyframes patternPulse {
 507 |     0% { transform: translate(-50%,-50%) scale(0); opacity: 1; }
 508 |     100% { transform: translate(-50%,-50%) scale(1); opacity: 0; }
 509 | }
 510 | .pn-disc-source {
 511 |     margin-top: 8px;
 512 |     font-family: 'JetBrains Mono', monospace;
 513 |     font-size: 9px;
 514 |     color: var(--pn-muted);
 515 | }
 516 | .pn-disc-source a { color: var(--pn-text-secondary); text-decoration: none; }
 517 | .pn-disc-source a:hover { color: var(--pn-red); }
 518 | 
 519 | /* ── TIER BADGE ANIMATION ─────────────────────────────────────── */
 520 | .pn-tier-badge {
 521 |     font-family: 'JetBrains Mono', monospace;
 522 |     font-size: 8px;
 523 |     font-weight: 800;
 524 |     letter-spacing: 2px;
 525 |     padding: 3px 10px;
 526 |     text-transform: uppercase;
 527 |     opacity: 0;
 528 |     transform: scale(0.8);
 529 |     animation: badgeReveal 0.4s ease forwards;
 530 | }
 531 | .pn-tier-badge.tier-1 {
 532 |     background: rgba(255,59,95,0.12);
 533 |     color: var(--pn-red);
 534 |     border: 1px solid rgba(255,59,95,0.25);
 535 |     animation-delay: 0.6s;
 536 | }
 537 | .pn-tier-badge.tier-2 {
 538 |     background: rgba(248,193,92,0.12);
 539 |     color: var(--pn-gold);
 540 |     border: 1px solid rgba(248,193,92,0.25);
 541 |     animation-delay: 0.7s;
 542 | }
 543 | @keyframes badgeReveal {
 544 |     to { opacity: 1; transform: scale(1); }
 545 | }
 546 | 
 547 | /* ── CORRELATION TIMELINE SVG ─────────────────────────────────── */
 548 | .pn-corr-timeline {
 549 |     margin: 12px 0;
 550 |     padding: 16px;
 551 |     background: var(--pn-surface);
 552 |     border: 1px solid var(--pn-border);
 553 |     overflow-x: auto;
 554 | }
 555 | .pn-corr-timeline svg {
 556 |     display: block;
 557 |     margin: 0 auto;
 558 |     overflow: visible;
 559 | }
 560 | .pn-corr-node {
 561 |     cursor: default;
 562 | }
 563 | .pn-corr-node circle {
 564 |     transition: r 0.3s ease;
 565 | }
 566 | .pn-corr-node:hover circle {
 567 |     r: 14;
 568 | }
 569 | .pn-corr-path {
 570 |     fill: none;
 571 |     stroke-linecap: round;
 572 |     animation: pathDraw 1.5s ease forwards;
 573 |     stroke-dasharray: 300;
 574 |     stroke-dashoffset: 300;
 575 | }
 576 | @keyframes pathDraw {
 577 |     to { stroke-dashoffset: 0; }
 578 | }
 579 | .pn-corr-summary {
 580 |     font-family: 'Inter', sans-serif;
 581 |     font-size: 12px;
 582 |     color: var(--pn-text-secondary);
 583 |     line-height: 1.5;
 584 |     margin: 10px 0;
 585 | }
 586 | .pn-corr-event-row {
 587 |     display: flex;
 588 |     align-items: center;
 589 |     gap: 8px;
 590 |     padding: 6px 10px;
 591 |     background: rgba(255,255,255,0.02);
 592 |     margin-bottom: 4px;
 593 |     font-family: 'JetBrains Mono', monospace;
 594 |     font-size: 10px;
 595 |     color: var(--pn-text-secondary);
 596 | }
 597 | .pn-corr-event-tag {
 598 |     font-size: 8px;
 599 |     font-weight: 800;
 600 |     letter-spacing: 1px;
 601 |     padding: 2px 6px;
 602 |     text-transform: uppercase;
 603 |     flex-shrink: 0;
 604 | }
 605 | .pn-corr-event-tag.disclosure { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 606 | .pn-corr-event-tag.whale { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 607 | .pn-corr-event-tag.geo { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
 608 | 
 609 | .pn-disclaimer-note {
 610 |     margin-bottom: 12px;
 611 |     padding: 8px 12px;
 612 |     background: rgba(255,59,95,0.03);
 613 |     border: 1px solid rgba(255,59,95,0.08);
 614 |     font-family: 'JetBrains Mono', monospace;
 615 |     font-size: 9px;
 616 |     color: var(--pn-muted);
 617 |     letter-spacing: 0.5px;
 618 |     line-height: 1.5;
 619 | }
 620 | 
 621 | /* ── WHALE CASCADE FEED ──────────────────────────────────────── */
 622 | .pn-whale-item {
 623 |     background: var(--pn-surface);
 624 |     border: 1px solid var(--pn-border);
 625 |     padding: 12px 14px;
 626 |     margin-bottom: 6px;
 627 |     position: relative;
 628 |     opacity: 0;
 629 |     transform: translateY(-20px);
 630 |     animation: whaleDrop 0.5s ease forwards;
 631 | }
 632 | .pn-whale-item:nth-child(1) { animation-delay: 0.1s; }
 633 | .pn-whale-item:nth-child(2) { animation-delay: 0.25s; }
 634 | .pn-whale-item:nth-child(3) { animation-delay: 0.4s; }
 635 | .pn-whale-item:nth-child(4) { animation-delay: 0.55s; }
 636 | .pn-whale-item:nth-child(5) { animation-delay: 0.7s; }
 637 | @keyframes whaleDrop {
 638 |     to { opacity: 1; transform: translateY(0); }
 639 | }
 640 | .pn-whale-item.inflow { border-left: 3px solid var(--pn-red); }
 641 | .pn-whale-item.outflow { border-left: 3px solid var(--pn-white); }
 642 | .pn-whale-row {
 643 |     display: flex;
 644 |     justify-content: space-between;
 645 |     align-items: center;
 646 |     margin-bottom: 4px;
 647 | }
 648 | .pn-whale-entity {
 649 |     font-size: 12px;
 650 |     font-weight: 600;
 651 |     color: var(--pn-white);
 652 | }
 653 | .pn-whale-type-tag {
 654 |     font-family: 'JetBrains Mono', monospace;
 655 |     font-size: 8px;
 656 |     font-weight: 700;
 657 |     letter-spacing: 1px;
 658 |     text-transform: uppercase;
 659 |     padding: 2px 6px;
 660 | }
 661 | .pn-whale-type-tag.inflow { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 662 | .pn-whale-type-tag.outflow { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 663 | .pn-whale-amt {
 664 |     font-family: 'JetBrains Mono', monospace;
 665 |     font-size: 20px;
 666 |     font-weight: 700;
 667 | }
 668 | .pn-whale-amt.inflow { color: var(--pn-red); }
 669 | .pn-whale-amt.outflow { color: var(--pn-white); }
 670 | .pn-whale-usd {
 671 |     font-family: 'JetBrains Mono', monospace;
 672 |     font-size: 11px;
 673 |     color: var(--pn-text-secondary);
 674 |     margin-bottom: 6px;
 675 | }
 676 | .pn-whale-meta {
 677 |     display: flex;
 678 |     justify-content: space-between;
 679 |     font-family: 'JetBrains Mono', monospace;
 680 |     font-size: 9px;
 681 |     color: var(--pn-muted);
 682 | }
 683 | .pn-whale-meta a { color: var(--pn-text-secondary); text-decoration: none; }
 684 | .pn-whale-meta a:hover { color: var(--pn-red); }
 685 | /* Whale size indicator (logarithmic glow bar) */
 686 | .pn-whale-size-bar {
 687 |     height: 2px;
 688 |     background: var(--pn-red);
 689 |     margin-top: 8px;
 690 |     border-radius: 1px;
 691 |     box-shadow: 0 0 6px rgba(255,59,95,0.4);
 692 |     transition: width 0.6s ease;
 693 | }
 694 | 
 695 | /* ── POLYMARKET ──────────────────────────────────────────────── */
 696 | .pn-poly-item {
 697 |     background: var(--pn-surface);
 698 |     border: 1px solid var(--pn-border);
 699 |     padding: 12px 14px;
 700 |     margin-bottom: 6px;
 701 | }
 702 | .pn-poly-question {
 703 |     font-size: 12px;
 704 |     font-weight: 600;
 705 |     color: var(--pn-white);
 706 |     margin-bottom: 8px;
 707 |     line-height: 1.3;
 708 | }
 709 | .pn-poly-row {
 710 |     display: flex;
 711 |     align-items: center;
 712 |     gap: 8px;
 713 |     margin-bottom: 6px;
 714 | }
 715 | .pn-poly-pct {
 716 |     font-family: 'JetBrains Mono', monospace;
 717 |     font-size: 20px;
 718 |     font-weight: 700;
 719 |     color: var(--pn-white);
 720 | }
 721 | .pn-poly-yes {
 722 |     font-family: 'JetBrains Mono', monospace;
 723 |     font-size: 9px;
 724 |     color: var(--pn-muted);
 725 |     text-transform: uppercase;
 726 | }
 727 | .pn-poly-signal {
 728 |     margin-left: auto;
 729 |     font-family: 'JetBrains Mono', monospace;
 730 |     font-size: 9px;
 731 |     font-weight: 700;
 732 |     letter-spacing: 1px;
 733 |     padding: 2px 6px;
 734 |     text-transform: uppercase;
 735 | }
 736 | .pn-poly-signal.bullish { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 737 | .pn-poly-signal.bearish { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 738 | .pn-poly-signal.neutral { background: rgba(255,255,255,0.03); color: var(--pn-muted); }
 739 | .pn-poly-bar {
 740 |     height: 3px;
 741 |     background: var(--pn-border);
 742 |     margin-bottom: 8px;
 743 |     overflow: hidden;
 744 | }
 745 | .pn-poly-bar-fill {
 746 |     height: 100%;
 747 |     transition: width 0.8s ease;
 748 | }
 749 | .pn-poly-bar-fill.bullish { background: var(--pn-white); }
 750 | .pn-poly-bar-fill.bearish { background: var(--pn-red); }
 751 | .pn-poly-bar-fill.neutral { background: var(--pn-muted); }
 752 | .pn-poly-meta {
 753 |     display: flex;
 754 |     gap: 12px;
 755 |     font-family: 'JetBrains Mono', monospace;
 756 |     font-size: 9px;
 757 |     color: var(--pn-muted);
 758 | }
 759 | .pn-poly-meta a { color: var(--pn-text-secondary); text-decoration: none; }
 760 | .pn-poly-meta a:hover { color: var(--pn-red); }
 761 | 
 762 | /* ── FOREX / NATION-STATE ────────────────────────────────────── */
 763 | .pn-forex-item {
 764 |     display: flex;
 765 |     justify-content: space-between;
 766 |     align-items: center;
 767 |     padding: 8px 12px;
 768 |     background: var(--pn-surface);
 769 |     border: 1px solid var(--pn-border);
 770 |     margin-bottom: 4px;
 771 | }
 772 | .pn-forex-pair {
 773 |     font-family: 'JetBrains Mono', monospace;
 774 |     font-size: 12px;
 775 |     font-weight: 700;
 776 |     color: var(--pn-white);
 777 | }
 778 | .pn-forex-rate {
 779 |     font-family: 'JetBrains Mono', monospace;
 780 |     font-size: 14px;
 781 |     font-weight: 700;
 782 |     color: var(--pn-gold);
 783 | }
 784 | 
 785 | /* ── GEOPOLITICAL ────────────────────────────────────────────── */
 786 | .pn-geo-item {
 787 |     background: var(--pn-surface);
 788 |     border: 1px solid var(--pn-border);
 789 |     padding: 12px 14px;
 790 |     margin-bottom: 6px;
 791 | }
 792 | .pn-geo-headline {
 793 |     font-size: 13px;
 794 |     font-weight: 600;
 795 |     color: var(--pn-white);
 796 |     margin-bottom: 8px;
 797 |     line-height: 1.3;
 798 | }
 799 | .pn-geo-signal-tag {
 800 |     display: inline-flex;
 801 |     align-items: center;
 802 |     gap: 4px;
 803 |     font-family: 'JetBrains Mono', monospace;
 804 |     font-size: 9px;
 805 |     font-weight: 700;
 806 |     letter-spacing: 1px;
 807 |     padding: 2px 8px;
 808 |     text-transform: uppercase;
 809 |     margin-bottom: 6px;
 810 | }
 811 | .pn-geo-signal-tag.bullish { background: rgba(255,255,255,0.06); color: var(--pn-white); }
 812 | .pn-geo-signal-tag.bearish { background: rgba(255,59,95,0.1); color: var(--pn-red); }
 813 | .pn-geo-signal-tag.neutral { background: rgba(255,255,255,0.03); color: var(--pn-muted); }
 814 | .pn-geo-rationale {
 815 |     font-family: 'JetBrains Mono', monospace;
 816 |     font-size: 10px;
 817 |     color: var(--pn-text-secondary);
 818 |     line-height: 1.4;
 819 |     margin-top: 6px;
 820 | }
 821 | .pn-geo-meta {
 822 |     margin-top: 8px;
 823 |     font-family: 'JetBrains Mono', monospace;
 824 |     font-size: 9px;
 825 |     color: var(--pn-muted);
 826 |     display: flex;
 827 |     justify-content: space-between;
 828 | }
 829 | 
 830 | /* ── WATCHLIST ────────────────────────────────────────────────── */
 831 | .pn-watchlist-item {
 832 |     display: flex;
 833 |     align-items: center;
 834 |     gap: 12px;
 835 |     padding: 8px 12px;
 836 |     background: var(--pn-surface);
 837 |     border: 1px solid var(--pn-border);
 838 |     margin-bottom: 4px;
 839 | }
 840 | .pn-watchlist-name {
 841 |     font-size: 12px;
 842 |     font-weight: 600;
 843 |     color: var(--pn-white);
 844 |     min-width: 120px;
 845 | }
 846 | .pn-watchlist-note {
 847 |     font-family: 'JetBrains Mono', monospace;
 848 |     font-size: 10px;
 849 |     color: var(--pn-text-secondary);
 850 |     flex: 1;
 851 | }
 852 | 
 853 | /* ── MAKE THE BITCOIN CASE ───────────────────────────────────── */
 854 | .pn-btc-case-btn {
 855 |     display: inline-flex;
 856 |     align-items: center;
 857 |     gap: 6px;
 858 |     background: transparent;
 859 |     border: 1px solid var(--pn-red);
 860 |     color: var(--pn-red);
 861 |     font-family: 'JetBrains Mono', monospace;
 862 |     font-size: 10px;
 863 |     font-weight: 700;
 864 |     letter-spacing: 1px;
 865 |     padding: 8px 16px;
 866 |     cursor: pointer;
 867 |     margin-top: 10px;
 868 |     transition: all 0.2s;
 869 |     text-transform: uppercase;
 870 | }
 871 | .pn-btc-case-btn:hover {
 872 |     background: rgba(255,59,95,0.08);
 873 | }
 874 | .pn-btc-case-btn:disabled {
 875 |     opacity: 0.5;
 876 |     cursor: not-allowed;
 877 | }
 878 | .pn-btc-case-output {
 879 |     display: none;
 880 |     margin-top: 10px;
 881 |     padding: 14px;
 882 |     background: var(--pn-surface);
 883 |     border: 1px solid rgba(248,193,92,0.15);
 884 |     font-family: 'JetBrains Mono', monospace;
 885 |     font-size: 11px;
 886 |     color: var(--pn-gold);
 887 |     line-height: 1.6;
 888 | }
 889 | .pn-btc-case-output.visible { display: block; }
 890 | .pn-btc-case-label {
 891 |     font-size: 8px;
 892 |     font-weight: 800;
 893 |     letter-spacing: 2px;
 894 |     color: var(--pn-gold);
 895 |     margin-bottom: 8px;
 896 |     opacity: 0.6;
 897 | }
 898 | .pn-typewriter-cursor {
 899 |     display: inline-block;
 900 |     width: 2px;
 901 |     height: 14px;
 902 |     background: var(--pn-gold);
 903 |     margin-left: 1px;
 904 |     animation: cursorBlink 0.5s step-end infinite;
 905 |     vertical-align: text-bottom;
 906 | }
 907 | @keyframes cursorBlink {
 908 |     50% { opacity: 0; }
 909 | }
 910 | .pn-btc-case-model {
 911 |     margin-top: 8px;
 912 |     font-size: 9px;
 913 |     color: var(--pn-muted);
 914 | }
 915 | 
 916 | /* ── CLASSIFIED OVERLAY ──────────────────────────────────────── */
 917 | .pn-classified-overlay {
 918 |     position: absolute;
 919 |     inset: 0;
 920 |     z-index: 10;
 921 |     backdrop-filter: blur(12px);
 922 |     -webkit-backdrop-filter: blur(12px);
 923 |     background: rgba(0,0,0,0.6);
 924 |     display: flex;
 925 |     flex-direction: column;
 926 |     align-items: center;
 927 |     justify-content: center;
 928 |     gap: 12px;
 929 | }
 930 | .pn-classified-stamp {
 931 |     font-family: 'JetBrains Mono', monospace;
 932 |     font-size: 28px;
 933 |     font-weight: 800;
 934 |     letter-spacing: 8px;
 935 |     color: var(--pn-red);
 936 |     text-transform: uppercase;
 937 |     transform: rotate(-8deg);
 938 |     border: 3px solid var(--pn-red);
 939 |     padding: 8px 24px;
 940 |     opacity: 0.85;
 941 |     text-shadow: 0 0 20px rgba(255,59,95,0.4);
 942 | }
 943 | .pn-classified-sub {
 944 |     font-family: 'JetBrains Mono', monospace;
 945 |     font-size: 11px;
 946 |     color: var(--pn-text-secondary);
 947 |     letter-spacing: 2px;
 948 | }
 949 | .pn-upgrade-btn {
 950 |     display: inline-block;
 951 |     padding: 10px 24px;
 952 |     background: var(--pn-red);
 953 |     color: var(--pn-white);
 954 |     font-family: 'JetBrains Mono', monospace;
 955 |     font-size: 11px;
 956 |     font-weight: 700;
 957 |     letter-spacing: 2px;
 958 |     text-transform: uppercase;
 959 |     text-decoration: none;
 960 |     transition: all 0.2s;
 961 |     margin-top: 4px;
 962 | }
 963 | .pn-upgrade-btn:hover {
 964 |     background: #e0304f;
 965 |     box-shadow: 0 0 20px rgba(255,59,95,0.3);
 966 | }
 967 | 
 968 | /* ── FALLBACK BANNER ─────────────────────────────────────────── */
 969 | .pn-fallback-banner {
 970 |     background: rgba(255,59,95,0.04);
 971 |     border: 1px solid rgba(255,59,95,0.15);
 972 |     padding: 10px 14px;
 973 |     margin-bottom: 12px;
 974 |     font-family: 'JetBrains Mono', monospace;
 975 |     font-size: 10px;
 976 |     color: var(--pn-red);
 977 |     letter-spacing: 0.5px;
 978 | }
 979 | 
 980 | /* ── EMPTY / LOADING ─────────────────────────────────────────── */
 981 | .pn-empty {
 982 |     font-family: 'JetBrains Mono', monospace;
 983 |     font-size: 11px;
 984 |     color: var(--pn-muted);
 985 |     padding: 20px;
 986 |     text-align: center;
 987 | }
 988 | .pn-loading {
 989 |     display: flex;
 990 |     align-items: center;
 991 |     justify-content: center;
 992 |     gap: 6px;
 993 |     font-family: 'JetBrains Mono', monospace;
 994 |     font-size: 10px;
 995 |     color: var(--pn-muted);
 996 |     padding: 20px;
 997 | }
 998 | .pn-loading-dot {
 999 |     width: 4px;
1000 |     height: 4px;
1001 |     border-radius: 50%;
1002 |     background: var(--pn-red);
1003 |     animation: loadDot 1.2s ease-in-out infinite;
1004 | }
1005 | .pn-loading-dot:nth-child(2) { animation-delay: 0.2s; }
1006 | .pn-loading-dot:nth-child(3) { animation-delay: 0.4s; }
1007 | @keyframes loadDot {
1008 |     0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
1009 |     40% { opacity: 1; transform: scale(1.2); }
1010 | }
1011 | 
1012 | /* ── HISTORICAL PRECEDENTS TIMELINE (GLASSMORPHIC REBUILD) ─── */
1013 | .pn-history {
1014 |     max-width: 1800px;
1015 |     margin: 0 auto;
1016 |     padding: 32px 16px 40px;
1017 |     position: relative;
1018 | }
1019 | .pn-history-header {
1020 |     font-family: 'JetBrains Mono', monospace;
1021 |     font-size: 13px;
1022 |     font-weight: 700;
1023 |     letter-spacing: 0.3em;
1024 |     text-transform: uppercase;
1025 |     color: var(--pn-red);
1026 |     margin-bottom: 6px;
1027 | }
1028 | .pn-history-subhead {
1029 |     font-family: 'Inter', sans-serif;
1030 |     font-size: 12px;
1031 |     color: var(--pn-muted);
1032 |     margin-bottom: 24px;
1033 |     line-height: 1.6;
1034 | }
1035 | .pn-timeline-scroll {
1036 |     overflow-x: auto;
1037 |     overflow-y: visible;
1038 |     -webkit-overflow-scrolling: touch;
1039 |     padding-bottom: 16px;
1040 |     scrollbar-width: thin;
1041 |     scrollbar-color: rgba(255,59,95,0.3) transparent;
1042 | }
1043 | .pn-timeline-scroll::-webkit-scrollbar { height: 4px; }
1044 | .pn-timeline-scroll::-webkit-scrollbar-thumb { background: rgba(255,59,95,0.3); border-radius: 2px; }
1045 | .pn-timeline {
1046 |     display: flex;
1047 |     align-items: center;
1048 |     position: relative;
1049 |     min-width: max-content;
1050 |     padding: 140px 40px 140px;
1051 | }
1052 | /* Glowing red timeline line */
1053 | .pn-timeline::before {
1054 |     content: '';
1055 |     position: absolute;
1056 |     top: 50%;
1057 |     left: 20px;
1058 |     right: 20px;
1059 |     height: 1px;
1060 |     background: var(--pn-red);
1061 |     opacity: 0.6;
1062 |     transform: translateY(-50%);
1063 |     animation: tlGlow 3s ease-in-out infinite;
1064 | }
1065 | @keyframes tlGlow {
1066 |     0%, 100% { box-shadow: 0 0 4px rgba(255,59,95,0.4); }
1067 |     50% { box-shadow: 0 0 12px rgba(255,59,95,0.6); }
1068 | }
1069 | /* Timeline node container */
1070 | .pn-tl-node {
1071 |     position: relative;
1072 |     flex: 0 0 auto;
1073 |     min-width: 110px;
1074 |     text-align: center;
1075 |     display: flex;
1076 |     flex-direction: column;
1077 |     align-items: center;
1078 | }
1079 | /* Above-line events: label on top, dot connects to line */
1080 | .pn-tl-node.tl-above {
1081 |     flex-direction: column-reverse;
1082 |     margin-bottom: 0;
1083 |     margin-top: -120px;
1084 | }
1085 | /* Below-line events */
1086 | .pn-tl-node.tl-below {
1087 |     margin-top: 120px;
1088 | }
1089 | /* Year label */
1090 | .pn-tl-year {
1091 |     font-family: 'JetBrains Mono', monospace;
1092 |     font-size: 11px;
1093 |     font-weight: 800;
1094 |     color: var(--pn-red);
1095 |     margin-bottom: 2px;
1096 |     white-space: nowrap;
1097 | }
1098 | .tl-above .pn-tl-year { margin-bottom: 0; margin-top: 2px; }
1099 | /* Event name */
1100 | .pn-tl-name {
1101 |     font-family: 'Inter', sans-serif;
1102 |     font-size: 10px;
1103 |     font-weight: 600;
1104 |     color: var(--pn-white);
1105 |     line-height: 1.3;
1106 |     max-width: 100px;
1107 |     margin-bottom: 6px;
1108 |     opacity: 0.85;
1109 | }
1110 | .tl-above .pn-tl-name { margin-bottom: 0; margin-top: 6px; }
1111 | /* Stem connecting dot to label area */
1112 | .pn-tl-stem {
1113 |     width: 1px;
1114 |     height: 30px;
1115 |     background: linear-gradient(to bottom, rgba(255,59,95,0.5), rgba(255,59,95,0.1));
1116 | }
1117 | .tl-above .pn-tl-stem {
1118 |     background: linear-gradient(to top, rgba(255,59,95,0.5), rgba(255,59,95,0.1));
1119 | }
1120 | /* The clickable pin dot */
1121 | .pn-tl-dot {
1122 |     width: 16px;
1123 |     height: 16px;
1124 |     border-radius: 50%;
1125 |     background: var(--pn-red);
1126 |     cursor: pointer;
1127 |     position: relative;
1128 |     flex-shrink: 0;
1129 |     transition: transform 0.2s, box-shadow 0.2s;
1130 |     box-shadow: 0 0 6px rgba(255,59,95,0.4);
1131 |     animation: pinPulse 2s ease-in-out infinite;
1132 |     z-index: 2;
1133 | }
1134 | @keyframes pinPulse {
1135 |     0%, 100% { box-shadow: 0 0 6px rgba(255,59,95,0.4), 0 0 0 0 rgba(255,59,95,0.3); }
1136 |     50% { box-shadow: 0 0 8px rgba(255,59,95,0.6), 0 0 0 6px rgba(255,59,95,0); }
1137 | }
1138 | .pn-tl-dot:hover {
1139 |     transform: scale(1.3);
1140 |     box-shadow: 0 0 14px rgba(255,59,95,0.7);
1141 | }
1142 | .pn-tl-dot.active {
1143 |     background: #fff;
1144 |     box-shadow: 0 0 16px rgba(255,59,95,0.8);
1145 |     animation: none;
1146 | }
1147 | /* Glassmorphic info card — fixed position to avoid clipping */
1148 | .pn-tl-card {
1149 |     position: fixed;
1150 |     max-width: 340px;
1151 |     min-width: 280px;
1152 |     background: rgba(0,0,0,0.88);
1153 |     backdrop-filter: blur(20px) saturate(180%);
1154 |     -webkit-backdrop-filter: blur(20px) saturate(180%);
1155 |     border: 1px solid rgba(255,59,95,0.4);
1156 |     border-radius: 12px;
1157 |     padding: 20px;
1158 |     text-align: left;
1159 |     opacity: 0;
1160 |     pointer-events: none;
1161 |     transform: translateY(-8px);
1162 |     transition: opacity 0.25s ease, transform 0.25s ease;
1163 |     z-index: 10000;
1164 |     box-shadow: 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05);
1165 | }
1166 | .pn-tl-card.active {
1167 |     opacity: 1;
1168 |     pointer-events: auto;
1169 |     transform: translateY(0);
1170 | }
1171 | .pn-tl-card-close {
1172 |     position: absolute;
1173 |     top: 10px;
1174 |     right: 12px;
1175 |     background: none;
1176 |     border: none;
1177 |     color: var(--pn-muted);
1178 |     font-size: 16px;
1179 |     cursor: pointer;
1180 |     padding: 2px 6px;
1181 |     line-height: 1;
1182 |     transition: color 0.2s;
1183 | }
1184 | .pn-tl-card-close:hover { color: var(--pn-white); }
1185 | .pn-tl-card-header {
1186 |     font-family: 'JetBrains Mono', monospace;
1187 |     font-size: 11px;
1188 |     font-weight: 700;
1189 |     color: var(--pn-red);
1190 |     text-transform: uppercase;
1191 |     letter-spacing: 1px;
1192 |     margin-bottom: 4px;
1193 |     padding-right: 24px;
1194 | }
1195 | .pn-tl-card-short {
1196 |     font-family: 'Inter', sans-serif;
1197 |     font-size: 13px;
1198 |     color: var(--pn-white);
1199 |     line-height: 1.7;
1200 |     margin-bottom: 10px;
1201 | }
1202 | .pn-tl-card-detail {
1203 |     font-family: 'Inter', sans-serif;
1204 |     font-size: 12px;
1205 |     color: rgba(255,255,255,0.7);
1206 |     line-height: 1.7;
1207 |     margin-bottom: 12px;
1208 | }
1209 | .pn-tl-card-btc {
1210 |     font-family: 'JetBrains Mono', monospace;
1211 |     font-size: 10px;
1212 |     color: var(--pn-red);
1213 |     padding: 8px 10px;
1214 |     background: rgba(255,59,95,0.08);
1215 |     border-left: 2px solid var(--pn-red);
1216 |     border-radius: 0 6px 6px 0;
1217 |     line-height: 1.5;
1218 | }
1219 | .pn-history-coda {
1220 |     font-family: 'JetBrains Mono', monospace;
1221 |     font-size: 11px;
1222 |     color: var(--pn-red);
1223 |     margin-top: 24px;
1224 |     line-height: 1.6;
1225 |     max-width: 800px;
1226 |     font-style: italic;
1227 |     opacity: 0.85;
1228 | }
1229 | 
1230 | /* ── DISCLAIMER ──────────────────────────────────────────────── */
1231 | .pn-disclaimer {
1232 |     padding: 20px 16px;
1233 |     font-family: 'JetBrains Mono', monospace;
1234 |     font-size: 9px;
1235 |     color: var(--pn-muted);
1236 |     line-height: 1.6;
1237 |     max-width: 1800px;
1238 |     margin: 0 auto;
1239 |     border-top: 1px solid var(--pn-border);
1240 | }
1241 | 
1242 | /* ── STATUS CHIP ─────────────────────────────────────────────── */
1243 | .pn-status-chip {
1244 |     font-family: 'JetBrains Mono', monospace;
1245 |     font-size: 8px;
1246 |     font-weight: 700;
1247 |     letter-spacing: 1px;
1248 |     text-transform: uppercase;
1249 |     padding: 2px 8px;
1250 | }
1251 | .pn-status-chip.loading { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
1252 | 
1253 | /* ── CONVICTION SCORE ────────────────────────────────────────── */
1254 | .pn-conviction {
1255 |     display: flex;
1256 |     align-items: center;
1257 |     gap: 6px;
1258 |     margin-top: 8px;
1259 |     padding: 6px 10px;
1260 |     background: rgba(255,255,255,0.02);
1261 |     border: 1px solid var(--pn-border);
1262 | }
1263 | .pn-conviction-label {
1264 |     font-family: 'JetBrains Mono', monospace;
1265 |     font-size: 8px;
1266 |     font-weight: 800;
1267 |     letter-spacing: 1.5px;
1268 |     text-transform: uppercase;
1269 |     color: var(--pn-muted);
1270 | }
1271 | .pn-conviction-score {
1272 |     font-family: 'JetBrains Mono', monospace;
1273 |     font-size: 14px;
1274 |     font-weight: 700;
1275 | }
1276 | .pn-conviction-score.high { color: var(--pn-red); }
1277 | .pn-conviction-score.medium { color: var(--pn-gold); }
1278 | .pn-conviction-score.low { color: var(--pn-muted); }
1279 | .pn-conviction-tag {
1280 |     font-family: 'JetBrains Mono', monospace;
1281 |     font-size: 8px;
1282 |     font-weight: 700;
1283 |     letter-spacing: 1px;
1284 |     padding: 2px 6px;
1285 |     text-transform: uppercase;
1286 | }
1287 | .pn-conviction-tag.high { background: rgba(255,59,95,0.12); color: var(--pn-red); }
1288 | .pn-conviction-tag.medium { background: rgba(248,193,92,0.12); color: var(--pn-gold); }
1289 | .pn-conviction-tag.low { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
1290 | .pn-conviction-bar {
1291 |     flex: 1;
1292 |     height: 3px;
1293 |     background: var(--pn-border);
1294 |     overflow: hidden;
1295 | }
1296 | .pn-conviction-bar-fill {
1297 |     height: 100%;
1298 |     transition: width 0.8s ease;
1299 | }
1300 | .pn-conviction-bar-fill.high { background: var(--pn-red); box-shadow: 0 0 6px rgba(255,59,95,0.4); }
1301 | .pn-conviction-bar-fill.medium { background: var(--pn-gold); }
1302 | .pn-conviction-bar-fill.low { background: var(--pn-muted); }
1303 | 
1304 | /* ── WHALE FLOW CLASSIFICATION ───────────────────────────────── */
1305 | .pn-whale-flow {
1306 |     margin-top: 6px;
1307 |     padding: 6px 10px;
1308 |     font-family: 'JetBrains Mono', monospace;
1309 |     font-size: 10px;
1310 |     line-height: 1.4;
1311 |     border-left: 2px solid var(--pn-border);
1312 | }
1313 | .pn-whale-flow.bullish {
1314 |     background: rgba(137,255,184,0.04);
1315 |     border-left-color: #89ffb8;
1316 |     color: #89ffb8;
1317 | }
1318 | .pn-whale-flow.bearish {
1319 |     background: rgba(255,59,95,0.04);
1320 |     border-left-color: var(--pn-red);
1321 |     color: var(--pn-red);
1322 | }
1323 | .pn-whale-flow.neutral {
1324 |     background: rgba(255,255,255,0.02);
1325 |     border-left-color: var(--pn-muted);
1326 |     color: var(--pn-text-secondary);
1327 | }
1328 | .pn-whale-flow-label {
1329 |     font-size: 8px;
1330 |     font-weight: 800;
1331 |     letter-spacing: 1.5px;
1332 |     text-transform: uppercase;
1333 |     margin-bottom: 2px;
1334 |     opacity: 0.7;
1335 | }
1336 | .pn-whale-signal-tag {
1337 |     font-family: 'JetBrains Mono', monospace;
1338 |     font-size: 8px;
1339 |     font-weight: 700;
1340 |     letter-spacing: 1px;
1341 |     padding: 2px 6px;
1342 |     text-transform: uppercase;
1343 |     margin-left: 8px;
1344 | }
1345 | .pn-whale-signal-tag.bullish { background: rgba(137,255,184,0.12); color: #89ffb8; }
1346 | .pn-whale-signal-tag.bearish { background: rgba(255,59,95,0.12); color: var(--pn-red); }
1347 | .pn-whale-signal-tag.neutral { background: rgba(255,255,255,0.04); color: var(--pn-muted); }
1348 | 
1349 | /* ── CORRELATION GAP COLORING ────────────────────────────────── */
1350 | .pn-corr-gap {
1351 |     font-family: 'JetBrains Mono', monospace;
1352 |     font-size: 11px;
1353 |     font-weight: 700;
1354 |     padding: 4px 8px;
1355 |     display: inline-flex;
1356 |     align-items: center;
1357 |     gap: 4px;
1358 |     margin-bottom: 6px;
1359 | }
1360 | .pn-corr-gap.red { background: rgba(255,59,95,0.12); color: var(--pn-red); }
1361 | .pn-corr-gap.orange { background: rgba(248,193,92,0.12); color: var(--pn-gold); }
1362 | .pn-corr-gap.white { background: rgba(255,255,255,0.06); color: var(--pn-white); }
1363 | 
1364 | /* ── POLYMARKET HERO MARKET ──────────────────────────────────── */
1365 | .pn-poly-hero {
1366 |     background: var(--pn-surface);
1367 |     border: 1px solid var(--pn-border);
1368 |     border-left: 3px solid var(--pn-gold);
1369 |     padding: 16px;
1370 |     margin-bottom: 10px;
1371 | }
1372 | .pn-poly-hero .pn-poly-question {
1373 |     font-size: 14px;
1374 |     font-weight: 700;
1375 |     margin-bottom: 10px;
1376 | }
1377 | .pn-poly-hero .pn-poly-pct {
1378 |     font-size: 28px;
1379 | }
1380 | .pn-poly-hero-bar {
1381 |     height: 6px;
1382 |     background: var(--pn-border);
1383 |     overflow: hidden;
1384 |     margin-bottom: 8px;
1385 |     position: relative;
1386 | }
1387 | .pn-poly-hero-bar-fill {
1388 |     height: 100%;
1389 |     background: linear-gradient(90deg, var(--pn-gold), var(--pn-red));
1390 |     transition: width 1.2s ease;
1391 |     position: relative;
1392 | }
1393 | .pn-poly-hero-bar-fill::after {
1394 |     content: '';
1395 |     position: absolute;
1396 |     right: 0;
1397 |     top: -2px;
1398 |     width: 2px;
1399 |     height: 10px;
1400 |     background: var(--pn-white);
1401 |     box-shadow: 0 0 6px rgba(255,255,255,0.6);
1402 |     animation: polyPulse 2s ease-in-out infinite;
1403 | }
1404 | @keyframes polyPulse {
1405 |     0%, 100% { opacity: 1; }
1406 |     50% { opacity: 0.3; }
1407 | }
1408 | .pn-poly-vol-badge {
1409 |     font-family: 'JetBrains Mono', monospace;
1410 |     font-size: 9px;
1411 |     font-weight: 700;
1412 |     color: var(--pn-gold);
1413 |     letter-spacing: 1px;
1414 | }
1415 | </style>
1416 | {% endblock %}
1417 | 
1418 | {% block body_class %}panopticon-body{% endblock %}
1419 | 
1420 | {% block content %}
1421 | 
1422 | <!-- ═══ STICKY TOP BAR ═══ -->
1423 | <div class="pn-topbar">
1424 |     <div class="pn-topbar-left">
1425 |         <span class="pn-topbar-logo">PANOPTICON</span>
1426 |         <div class="pn-topbar-status">
1427 |             <div class="pn-topbar-dot"></div>
1428 |             <span>SCANNING</span>
1429 |         </div>
1430 |     </div>
1431 |     <div class="pn-topbar-right">
1432 |         <span class="pn-topbar-btc" id="pnBtcPrice">
1433 |             {% if data.btc_price %}BTC ${{ "{:,.0f}".format(data.btc_price) }}{% else %}BTC --{% endif %}
1434 |         </span>
1435 |         <span class="pn-topbar-clock" id="pnClock">--:--:-- UTC</span>
1436 |         <a href="/" class="pn-topbar-back">&larr; PROTOCOL PULSE</a>
1437 |     </div>
1438 | </div>
1439 | 
1440 | <!-- ═══ HERO — RADAR SWEEP ═══ -->
1441 | <section class="pn-hero">
1442 |     <div class="pn-hero-radar">
1443 |         <div class="pn-radar-rings">
1444 |             <div class="pn-radar-ring"></div>
1445 |             <div class="pn-radar-ring"></div>
1446 |             <div class="pn-radar-ring"></div>
1447 |             <div class="pn-radar-ring"></div>
1448 |         </div>
1449 |         <div class="pn-radar-cross"></div>
1450 |         <div class="pn-radar-sweep"></div>
1451 |         <div class="pn-scanlines"></div>
1452 |     </div>
1453 |     <div class="pn-hero-content">
1454 |         <h1 class="pn-hero-title">PANOPTICON</h1>
1455 |         <p class="pn-hero-tagline">They watch us. Now we watch them.</p>
1456 | 
1457 |         <div class="pn-hero-stats">
1458 |             <div class="pn-hero-stat">
1459 |                 <div class="pn-hero-stat-val" id="pnStatDisc">{{ data.disclosures|length }}</div>
1460 |                 <div class="pn-hero-stat-label">Disclosures</div>
1461 |             </div>
1462 |             <div class="pn-hero-stat-sep"></div>
1463 |             <div class="pn-hero-stat">
1464 |                 <div class="pn-hero-stat-val" id="pnStatWhales">{{ data.whales|length }}</div>
1465 |                 <div class="pn-hero-stat-label">Whale Moves</div>
1466 |             </div>
1467 |             <div class="pn-hero-stat-sep"></div>
1468 |             <div class="pn-hero-stat">
1469 |                 <div class="pn-hero-stat-val" id="pnStatFlags">{{ data.flagged|length }}</div>
1470 |                 <div class="pn-hero-stat-label">Patterns</div>
1471 |             </div>
1472 |             <div class="pn-hero-stat-sep"></div>
1473 |             <div class="pn-hero-stat">
1474 |                 <div class="pn-hero-stat-val" id="pnStatEvents">{{ data.events_today }}</div>
1475 |                 <div class="pn-hero-stat-label">Events Today</div>
1476 |             </div>
1477 |         </div>
1478 |     </div>
1479 | </section>
1480 | 
1481 | <!-- ═══ LIVE TICKER ═══ -->
1482 | <div class="pn-ticker">
1483 |     <span class="pn-ticker-tag">LIVE FEED</span>
1484 |     <div class="pn-ticker-scroll">
1485 |         <span class="pn-ticker-text">
1486 |             {% if data.whales %}{% for w in data.whales[:3] %}{{ w.entity }}: {{ w.amount_btc }} BTC {{ w.tx_type }} &nbsp;&bull;&nbsp; {% endfor %}{% endif %}{% for d in data.disclosures[:3] %}{{ d.entity }} &mdash; {{ d.asset }} ({{ d.trade_type }}) &nbsp;&bull;&nbsp; {% endfor %}PANOPTICON monitoring {{ data.events_today }} events &nbsp;&bull;&nbsp; All data from public sources &nbsp;&bull;&nbsp; {% if data.whales %}{% for w in data.whales[:3] %}{{ w.entity }}: {{ w.amount_btc }} BTC {{ w.tx_type }} &nbsp;&bull;&nbsp; {% endfor %}{% endif %}{% for d in data.disclosures[:3] %}{{ d.entity }} &mdash; {{ d.asset }} ({{ d.trade_type }}) &nbsp;&bull;&nbsp; {% endfor %}PANOPTICON monitoring {{ data.events_today }} events &nbsp;&bull;&nbsp;
1487 |         </span>
1488 |     </div>
1489 | </div>
1490 | 
1491 | {% if demo_mode %}
1492 | <!-- ═══ CLASSIFIED ALERT BAR ═══ -->
1493 | <div style="display:flex;align-items:center;padding:8px 16px;background:rgba(255,59,95,0.04);border-bottom:1px solid var(--pn-border);gap:12px;">
1494 |     <div style="display:flex;align-items:center;gap:6px;">
1495 |         <div class="pn-topbar-dot"></div>
1496 |         <span style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;color:var(--pn-red);letter-spacing:1px;">CLASSIFIED — COMMANDER ACCESS REQUIRED</span>
1497 |     </div>
1498 |     <a href="/join" style="margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--pn-muted);text-decoration:none;letter-spacing:1px;">Upgrade &rarr;</a>
1499 | </div>
1500 | {% endif %}
1501 | 
1502 | <!-- ═══════════════════════════════════════════════════════════════════════
1503 |      SOVEREIGN SIGNAL v2 — MISSION CONTROL INTELLIGENCE PANEL
1504 |      Replaces the orb/radar. Live data from APIs. Every element is analytical.
1505 |      ════════════════════════════════════════════════════════════════════════ -->
1506 | <div id="ss2-root">
1507 | 
1508 | <!-- ── HEADER ── -->
1509 | <div id="ss2-header">
1510 |   <div>
1511 |     <div class="ss2-overline">PROTOCOL PULSE · INTELLIGENCE SYNTHESIS · LIVE</div>
1512 |     <div class="ss2-title">SOVEREIGN SIGNAL</div>
1513 |   </div>
1514 |   <div id="ss2-composite-block">
1515 |     <div class="ss2-overline" style="text-align:right;">CONVERGENCE INDEX</div>
1516 |     <div id="ss2-score-display">
1517 |       <span id="ss2-score-num">—</span><span class="ss2-score-denom">/100</span>
1518 |     </div>
1519 |     <div id="ss2-verdict">▋ LOADING STREAMS...</div>
1520 |   </div>
1521 | </div>
1522 | 
1523 | <!-- ── SIX ARC GAUGES ── -->
1524 | <div id="ss2-gauges-row">
1525 |   <div class="ss2-gauge-cell" id="gc-congress"   data-stream="congress">
1526 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1527 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1528 |       <path class="ss2-arc-fill" id="ga-congress" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1529 |       <line class="ss2-needle" id="gn-congress" x1="60" y1="65" x2="60" y2="20"/>
1530 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1531 |       <text class="ss2-gauge-score" id="gs-congress" x="60" y="58">—</text>
1532 |     </svg>
1533 |     <div class="ss2-gauge-label">CONGRESS</div>
1534 |     <div class="ss2-gauge-sub" id="gd-congress">IHX · INSIDER TRADES</div>
1535 |     <div class="ss2-gauge-arrow" id="garr-congress">—</div>
1536 |   </div>
1537 |   <div class="ss2-gauge-cell" id="gc-pac" data-stream="pac">
1538 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1539 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1540 |       <path class="ss2-arc-fill" id="ga-pac" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1541 |       <line class="ss2-needle" id="gn-pac" x1="60" y1="65" x2="60" y2="20"/>
1542 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1543 |       <text class="ss2-gauge-score" id="gs-pac" x="60" y="58">—</text>
1544 |     </svg>
1545 |     <div class="ss2-gauge-label">PAC CAPITAL</div>
1546 |     <div class="ss2-gauge-sub" id="gd-pac">FAIRSHAKE · POLITICAL SPEND</div>
1547 |     <div class="ss2-gauge-arrow" id="garr-pac">—</div>
1548 |   </div>
1549 |   <div class="ss2-gauge-cell" id="gc-legislation" data-stream="legislation">
1550 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1551 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1552 |       <path class="ss2-arc-fill" id="ga-legislation" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1553 |       <line class="ss2-needle" id="gn-legislation" x1="60" y1="65" x2="60" y2="20"/>
1554 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1555 |       <text class="ss2-gauge-score" id="gs-legislation" x="60" y="58">—</text>
1556 |     </svg>
1557 |     <div class="ss2-gauge-label">LEGISLATION</div>
1558 |     <div class="ss2-gauge-sub" id="gd-legislation">BILL MOMENTUM · VOTES</div>
1559 |     <div class="ss2-gauge-arrow" id="garr-legislation">—</div>
1560 |   </div>
1561 |   <div class="ss2-gauge-cell" id="gc-onchain" data-stream="onchain">
1562 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1563 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1564 |       <path class="ss2-arc-fill" id="ga-onchain" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1565 |       <line class="ss2-needle" id="gn-onchain" x1="60" y1="65" x2="60" y2="20"/>
1566 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1567 |       <text class="ss2-gauge-score" id="gs-onchain" x="60" y="58">—</text>
1568 |     </svg>
1569 |     <div class="ss2-gauge-label">ON-CHAIN</div>
1570 |     <div class="ss2-gauge-sub" id="gd-onchain">HASHRATE · ACCUMULATION</div>
1571 |     <div class="ss2-gauge-arrow" id="garr-onchain">—</div>
1572 |   </div>
1573 |   <div class="ss2-gauge-cell" id="gc-institutional" data-stream="institutional">
1574 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1575 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1576 |       <path class="ss2-arc-fill" id="ga-institutional" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1577 |       <line class="ss2-needle" id="gn-institutional" x1="60" y1="65" x2="60" y2="20"/>
1578 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1579 |       <text class="ss2-gauge-score" id="gs-institutional" x="60" y="58">—</text>
1580 |     </svg>
1581 |     <div class="ss2-gauge-label">INSTITUTIONAL</div>
1582 |     <div class="ss2-gauge-sub" id="gd-institutional">13F · FORM D · EDGAR</div>
1583 |     <div class="ss2-gauge-arrow" id="garr-institutional">—</div>
1584 |   </div>
1585 |   <div class="ss2-gauge-cell" id="gc-geo" data-stream="geo">
1586 |     <svg class="ss2-gauge-svg" viewBox="0 0 120 70">
1587 |       <path class="ss2-arc-bg"  d="M10,65 A50,50 0 0,1 110,65"/>
1588 |       <path class="ss2-arc-fill" id="ga-geo" d="M10,65 A50,50 0 0,1 110,65" stroke-dasharray="0 157"/>
1589 |       <line class="ss2-needle" id="gn-geo" x1="60" y1="65" x2="60" y2="20"/>
1590 |       <circle cx="60" cy="65" r="4" class="ss2-needle-hub"/>
1591 |       <text class="ss2-gauge-score" id="gs-geo" x="60" y="58">—</text>
1592 |     </svg>
1593 |     <div class="ss2-gauge-label">GEOPOLITICAL</div>
1594 |     <div class="ss2-gauge-sub" id="gd-geo">MACRO · NATION-STATE</div>
1595 |     <div class="ss2-gauge-arrow" id="garr-geo">—</div>
1596 |   </div>
1597 | </div>
1598 | 
1599 | <!-- ── HOVER DATA CARD ── -->
1600 | <div id="ss2-datacard">
1601 |   <div id="ss2-dc-header">
1602 |     <div>
1603 |       <div id="ss2-dc-stream" class="ss2-overline"></div>
1604 |       <div id="ss2-dc-title"></div>
1605 |     </div>
1606 |     <div id="ss2-dc-score-wrap">
1607 |       <div id="ss2-dc-score"></div>
1608 |       <div id="ss2-dc-verdict"></div>
1609 |     </div>
1610 |   </div>
1611 |   <div id="ss2-dc-rows"></div>
1612 |   <div id="ss2-dc-insight"></div>
1613 | </div>
1614 | 
1615 | <!-- ── MIDDLE ROW: CORRELATION MAP + SIGNAL BOARD ── -->
1616 | <div id="ss2-middle">
1617 | 
1618 |   <!-- Correlation scatter map -->
1619 |   <div id="ss2-map-wrap">
1620 |     <div class="ss2-overline" style="padding:12px 16px 8px;">SIGNAL CORRELATION MAP  <span style="color:rgba(255,255,255,0.45);font-weight:400;">· HOVER FOR DRILL-DOWN</span></div>
1621 |     <div style="position:relative;">
1622 |       <canvas id="ss2-map-canvas"></canvas>
1623 |       <div id="ss2-map-tooltip"></div>
1624 |     </div>
1625 |     <!-- Axis labels -->
1626 |     <div id="ss2-axis-wrap">
1627 |       <div style="font-size:clamp(8px,0.6vw,11px);color:rgba(255,255,255,0.4);letter-spacing:.15em;">← BEARISH &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; BULLISH →</div>
1628 |       <div style="font-size:clamp(8px,0.6vw,11px);color:rgba(255,255,255,0.4);letter-spacing:.15em;">STRENGTH AXIS</div>
1629 |     </div>
1630 |   </div>
1631 | 
1632 |   <!-- Signal Board -->
1633 |   <div id="ss2-board-wrap">
1634 |     <div class="ss2-overline" style="padding:12px 16px 8px;display:flex;justify-content:space-between;">
1635 |       <span>LIVE SIGNAL BOARD</span>
1636 |       <span id="ss2-board-ts" style="color:rgba(255,255,255,0.4);font-weight:400;font-size:clamp(8px,0.6vw,10px);letter-spacing:.1em;"></span>
1637 |     </div>
1638 |     <div id="ss2-signal-board"></div>
1639 |   </div>
1640 | 
1641 | </div>
1642 | 
1643 | <!-- ── BOTTOM: DATA BARS WATERFALL ── -->
1644 | <div id="ss2-waterfall">
1645 |   <div class="ss2-overline" style="padding:10px 16px 8px;">CONVERGENCE WATERFALL  <span style="color:rgba(255,255,255,0.45);font-weight:400;">· CONTRIBUTION TO 74/100</span></div>
1646 |   <div id="ss2-waterfall-bars"></div>
1647 |   <div style="padding:6px 16px 10px;font-size:7px;color:rgba(255,255,255,0.12);font-family:'JetBrains Mono',monospace;">
1648 |     SOURCE: OPENFEC · SEC EDGAR · LEGISCAN CC BY 4.0 · MEMPOOL.SPACE · POLYMARKET &nbsp;·&nbsp; NOT FINANCIAL ADVICE
1649 |   </div>
1650 | </div>
1651 | 
1652 | </div><!-- #ss2-root -->
1653 | 
1654 | <!-- ── STYLES ── -->
1655 | <style>
1656 | #ss2-root {
1657 |   font-family: 'JetBrains Mono', 'Courier New', monospace;
1658 |   background: #030303;
1659 |   border-top: 1px solid rgba(204,0,0,0.25);
1660 |   border-bottom: 1px solid rgba(204,0,0,0.18);
1661 |   color: #fff;
1662 |   position: relative;
1663 |   overflow: hidden;
1664 | }
1665 | #ss2-root::before {
1666 |   content: '';
1667 |   position: absolute;
1668 |   inset: 0;
1669 |   background:
1670 |     repeating-linear-gradient(0deg, transparent, transparent 47px, rgba(204,0,0,0.025) 47px, rgba(204,0,0,0.025) 48px),
1671 |     repeating-linear-gradient(90deg, transparent, transparent 47px, rgba(204,0,0,0.025) 47px, rgba(204,0,0,0.025) 48px);
1672 |   pointer-events: none;
1673 |   z-index: 0;
1674 | }
1675 | #ss2-root > * { position: relative; z-index: 1; }
1676 | 
1677 | .ss2-overline {
1678 |   font-size: clamp(8px, 0.6vw, 11px);
1679 |   letter-spacing: .25em;
1680 |   color: rgba(204,0,0,.7);
1681 |   font-weight: 700;
1682 |   text-transform: uppercase;
1683 | }
1684 | .ss2-title {
1685 |   font-size: 22px;
1686 |   font-weight: 900;
1687 |   letter-spacing: .12em;
1688 |   color: #fff;
1689 |   line-height: 1;
1690 |   margin-top: 5px;
1691 | }
1692 | 
1693 | /* Header */
1694 | #ss2-header {
1695 |   display: flex;
1696 |   justify-content: space-between;
1697 |   align-items: flex-start;
1698 |   padding: 16px 20px 12px;
1699 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1700 | }
1701 | #ss2-composite-block { text-align: right; }
1702 | #ss2-score-display {
1703 |   display: flex;
1704 |   align-items: baseline;
1705 |   gap: 3px;
1706 |   justify-content: flex-end;
1707 |   margin-top: 4px;
1708 | }
1709 | #ss2-score-num {
1710 |   font-size: 56px;
1711 |   font-weight: 900;
1712 |   line-height: 1;
1713 |   color: #CC0000;
1714 |   text-shadow: 0 0 30px rgba(204,0,0,.55);
1715 |   transition: color .5s;
1716 | }
1717 | .ss2-score-denom { font-size: 16px; color: rgba(255,255,255,.2); }
1718 | #ss2-verdict {
1719 |   font-size: 9px;
1720 |   letter-spacing: .1em;
1721 |   margin-top: 3px;
1722 |   transition: color .5s;
1723 | }
1724 | 
1725 | /* Gauges row */
1726 | #ss2-gauges-row {
1727 |   display: grid;
1728 |   grid-template-columns: repeat(6, 1fr);
1729 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1730 | }
1731 | .ss2-gauge-cell {
1732 |   padding: 14px clamp(10px, 1.5vw, 18px) 10px;
1733 |   border-right: 1px solid rgba(255,255,255,0.04);
1734 |   cursor: pointer;
1735 |   transition: background .15s;
1736 |   position: relative;
1737 | }
1738 | .ss2-gauge-cell:last-child { border-right: none; }
1739 | .ss2-gauge-cell:hover, .ss2-gauge-cell.active { background: rgba(204,0,0,.05); }
1740 | .ss2-gauge-cell.active { background: rgba(204,0,0,.08); }
1741 | 
1742 | .ss2-gauge-svg {
1743 |   width: 100%;
1744 |   height: auto;
1745 |   display: block;
1746 |   margin-bottom: 6px;
1747 |   overflow: visible;
1748 | }
1749 | .ss2-arc-bg {
1750 |   fill: none;
1751 |   stroke: rgba(255,255,255,.06);
1752 |   stroke-width: 5;
1753 |   stroke-linecap: round;
1754 | }
1755 | .ss2-arc-fill {
1756 |   fill: none;
1757 |   stroke-width: 5;
1758 |   stroke-linecap: round;
1759 |   stroke: #f8c15c;
1760 |   transition: stroke-dasharray 1.2s cubic-bezier(.22,.61,.36,1);
1761 | }
1762 | .ss2-needle {
1763 |   stroke: rgba(255,255,255,.7);
1764 |   stroke-width: 1.5;
1765 |   stroke-linecap: round;
1766 |   transform-origin: 60px 65px;
1767 |   transition: transform 1.4s cubic-bezier(.34,1.56,.64,1);
1768 | }
1769 | .ss2-needle-hub {
1770 |   fill: rgba(255,255,255,.9);
1771 | }
1772 | .ss2-gauge-score {
1773 |   font-family: 'JetBrains Mono', monospace;
1774 |   font-size: 14px;
1775 |   font-weight: 900;
1776 |   text-anchor: middle;
1777 |   fill: #fff;
1778 | }
1779 | .ss2-gauge-label {
1780 |   font-size: clamp(9px, 0.75vw, 13px);
1781 |   font-weight: 700;
1782 |   letter-spacing: .12em;
1783 |   text-align: center;
1784 |   color: rgba(255,255,255,.85);
1785 | }
1786 | .ss2-gauge-sub {
1787 |   font-size: clamp(8px, 0.6vw, 11px);
1788 |   color: rgba(255,255,255,.45);
1789 |   text-align: center;
1790 |   margin-top: 3px;
1791 |   letter-spacing: .04em;
1792 |   line-height: 1.4;
1793 | }
1794 | .ss2-gauge-arrow {
1795 |   font-size: 10px;
1796 |   text-align: center;
1797 |   margin-top: 4px;
1798 |   transition: color .5s;
1799 |   letter-spacing: .06em;
1800 | }
1801 | 
1802 | /* Data Card */
1803 | #ss2-datacard {
1804 |   display: none;
1805 |   background: rgba(5,5,5,.97);
1806 |   border: 1px solid rgba(204,0,0,.45);
1807 |   border-radius: 4px;
1808 |   padding: 18px 20px;
1809 |   position: absolute;
1810 |   top: 100px;
1811 |   left: 50%;
1812 |   transform: translateX(-50%);
1813 |   z-index: 50;
1814 |   box-shadow: 0 16px 48px rgba(0,0,0,.85), 0 0 24px rgba(204,0,0,.12);
1815 |   width: 580px;
1816 |   max-width: calc(100% - 40px);
1817 |   animation: ss2FadeIn .15s ease;
1818 | }
1819 | #ss2-datacard.visible { display: block; }
1820 | @keyframes ss2FadeIn { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }
1821 | #ss2-dc-header {
1822 |   display: flex;
1823 |   justify-content: space-between;
1824 |   align-items: flex-start;
1825 |   margin-bottom: 10px;
1826 |   padding-bottom: 10px;
1827 |   border-bottom: 1px solid rgba(255,255,255,.06);
1828 | }
1829 | #ss2-dc-title {
1830 |   font-size: 13px;
1831 |   font-weight: 700;
1832 |   color: #fff;
1833 |   margin-top: 4px;
1834 | }
1835 | #ss2-dc-score { font-size: 32px; font-weight: 900; line-height: 1; }
1836 | #ss2-dc-verdict { font-size: 8px; letter-spacing: .1em; margin-top: 2px; }
1837 | #ss2-dc-rows {
1838 |   display: grid;
1839 |   grid-template-columns: 1fr 1fr;
1840 |   gap: 5px 20px;
1841 |   margin-bottom: 10px;
1842 | }
1843 | .ss2-dc-row {
1844 |   display: flex;
1845 |   justify-content: space-between;
1846 |   align-items: baseline;
1847 |   padding: 4px 0;
1848 |   border-bottom: 1px solid rgba(255,255,255,.04);
1849 |   font-size: 9px;
1850 | }
1851 | .ss2-dc-key { color: rgba(255,255,255,.35); }
1852 | .ss2-dc-val { color: rgba(255,255,255,.9); font-weight: 700; }
1853 | .ss2-dc-val.hot { color: #CC0000; }
1854 | .ss2-dc-val.gold { color: #f8c15c; }
1855 | .ss2-dc-val.green { color: #22c55e; }
1856 | #ss2-dc-insight {
1857 |   font-size: 8.5px;
1858 |   color: rgba(255,255,255,.38);
1859 |   line-height: 1.6;
1860 |   border-top: 1px solid rgba(255,255,255,.04);
1861 |   padding-top: 8px;
1862 |   font-style: italic;
1863 | }
1864 | 
1865 | /* Middle row */
1866 | #ss2-middle {
1867 |   display: grid;
1868 |   grid-template-columns: 1fr 400px;
1869 |   border-bottom: 1px solid rgba(255,255,255,0.04);
1870 |   min-height: 340px;
1871 | }
1872 | #ss2-map-wrap {
1873 |   border-right: 1px solid rgba(255,255,255,0.04);
1874 |   display: flex;
1875 |   flex-direction: column;
1876 | }
1877 | #ss2-map-canvas {
1878 |   display: block;
1879 |   width: 100%;
1880 |   flex: 1;
1881 |   min-height: 280px;
1882 | }
1883 | #ss2-axis-wrap {
1884 |   display: flex;
1885 |   justify-content: space-between;
1886 |   padding: 4px 16px 8px;
1887 | }
1888 | #ss2-map-tooltip {
1889 |   position: absolute;
1890 |   pointer-events: none;
1891 |   opacity: 0;
1892 |   background: rgba(5,5,5,.95);
1893 |   border: 1px solid rgba(204,0,0,.4);
1894 |   border-radius: 3px;
1895 |   padding: 8px 10px;
1896 |   font-size: 9px;
1897 |   color: rgba(255,255,255,.8);
1898 |   transition: opacity .12s;
1899 |   z-index: 30;
1900 |   min-width: 140px;
1901 |   line-height: 1.6;
1902 | }
1903 | 
1904 | /* Signal Board */
1905 | #ss2-board-wrap { overflow: hidden; display: flex; flex-direction: column; }
1906 | #ss2-signal-board {
1907 |   padding: 4px 0;
1908 |   overflow-y: auto;
1909 |   flex: 1;
1910 |   max-height: 310px;
1911 | }
1912 | #ss2-signal-board::-webkit-scrollbar { width: 3px; }
1913 | #ss2-signal-board::-webkit-scrollbar-track { background: transparent; }
1914 | #ss2-signal-board::-webkit-scrollbar-thumb { background: rgba(204,0,0,0.3); border-radius: 2px; }
1915 | .ss2-signal-item {
1916 |   display: flex;
1917 |   align-items: flex-start;
1918 |   gap: 10px;
1919 |   padding: 9px 16px;
1920 |   border-bottom: 1px solid rgba(255,255,255,.04);
1921 |   cursor: default;
1922 |   transition: background .12s;
1923 | }
1924 | .ss2-signal-item:hover { background: rgba(255,255,255,.025); }
1925 | .ss2-si-dot {
1926 |   width: 7px;
1927 |   height: 7px;
1928 |   border-radius: 50%;
1929 |   flex-shrink: 0;
1930 |   margin-top: 4px;
1931 | }
1932 | .ss2-si-body { flex: 1; min-width: 0; }
1933 | .ss2-si-label {
1934 |   font-size: 7.5px;
1935 |   letter-spacing: .14em;
1936 |   margin-bottom: 3px;
1937 | }
1938 | .ss2-si-text {
1939 |   font-size: 10px;
1940 |   color: rgba(255,255,255,.75);
1941 |   line-height: 1.5;
1942 |   white-space: normal;
1943 | }
1944 | .ss2-si-val {
1945 |   font-size: 11px;
1946 |   font-weight: 700;
1947 |   flex-shrink: 0;
1948 |   text-align: right;
1949 |   min-width: 48px;
1950 | }
1951 | 
1952 | /* Waterfall */
1953 | #ss2-waterfall { border-top: 1px solid rgba(255,255,255,0.04); }
1954 | #ss2-waterfall-bars {
1955 |   display: grid;
1956 |   grid-template-columns: repeat(6, 1fr);
1957 |   gap: 1px;
1958 |   padding: 0 20px 14px;
1959 | }
1960 | .ss2-wf-col {
1961 |   padding: 4px 8px;
1962 |   cursor: pointer;
1963 |   transition: background .12s;
1964 |   border-right: 1px solid rgba(255,255,255,0.03);
1965 | }
1966 | .ss2-wf-col:last-child { border-right: none; }
1967 | .ss2-wf-col:hover { background: rgba(255,255,255,.025); }
1968 | .ss2-wf-bar-wrap {
1969 |   height: 38px;
1970 |   display: flex;
1971 |   align-items: flex-end;
1972 |   justify-content: center;
1973 |   margin-bottom: 5px;
1974 |   gap: 2px;
1975 | }
1976 | .ss2-wf-bar {
1977 |   width: 50%;
1978 |   border-radius: 2px 2px 0 0;
1979 |   min-height: 2px;
1980 |   transition: height 1.5s cubic-bezier(.22,.61,.36,1);
1981 | }
1982 | .ss2-wf-score {
1983 |   font-size: 11px;
1984 |   font-weight: 900;
1985 |   text-align: center;
1986 |   margin-bottom: 3px;
1987 | }
1988 | .ss2-wf-label {
1989 |   font-size: 7px;
1990 |   color: rgba(255,255,255,.4);
1991 |   text-align: center;
1992 |   letter-spacing: .08em;
1993 |   line-height: 1.5;
1994 | }
1995 | .ss2-wf-contrib {
1996 |   font-size: 6.5px;
1997 |   color: rgba(255,255,255,.18);
1998 |   text-align: center;
1999 |   margin-top: 3px;
2000 | }
2001 | 
2002 | @media(max-width:1100px) {
2003 |   #ss2-middle { grid-template-columns: 1fr 340px; }
2004 | }
2005 | @media(max-width:900px) {
2006 |   #ss2-middle { grid-template-columns: 1fr; min-height: auto; }
2007 |   #ss2-map-canvas { min-height: 220px; }
2008 |   #ss2-board-wrap { border-top: 1px solid rgba(255,255,255,0.04); }
2009 | }
2010 | @media(max-width:768px) {
2011 |   #ss2-gauges-row { grid-template-columns: repeat(3,1fr); }
2012 |   #ss2-waterfall-bars { grid-template-columns: repeat(3,1fr); }
2013 | }
2014 | @media(max-width:480px) {
2015 |   #ss2-gauges-row { grid-template-columns: repeat(2,1fr); }
2016 |   #ss2-waterfall-bars { grid-template-columns: repeat(2,1fr); }
2017 |   #ss2-score-num { font-size: 40px; }
2018 | }
2019 | </style>
2020 | 
2021 | <!-- ── JAVASCRIPT ── -->
2022 | <script>
2023 | (function() {
2024 | 'use strict';
2025 | 
2026 | // ─── Stream definitions ─────────────────────────────────────────────────────
2027 | var STREAMS = {
2028 |   congress:    { label:'CONGRESS',      sub:'IHX · INSIDER TRADES',   color:'#f8c15c', apiKey:'ihx' },
2029 |   pac:         { label:'PAC CAPITAL',   sub:'FAIRSHAKE · SPEND',       color:'#CC0000', apiKey:'pac' },
2030 |   legislation: { label:'LEGISLATION',   sub:'BILL MOMENTUM',           color:'#22c55e', apiKey:'leg' },
2031 |   onchain:     { label:'ON-CHAIN',      sub:'HASHRATE · ACCUM',        color:'#f8c15c', apiKey:'orb' },
2032 |   institutional:{ label:'INSTITUTIONAL',sub:'13F · FORM D',            color:'#22c55e', apiKey:'inst' },
2033 |   geo:         { label:'GEOPOLITICAL',  sub:'MACRO · NATION-STATE',    color:'#22c55e', apiKey:'orb' },
2034 | };
2035 | 
2036 | var streamOrder = ['congress','pac','legislation','onchain','institutional','geo'];
2037 | var liveData = {};   // filled by API calls
2038 | var scores = {};     // filled after data arrives
2039 | 
2040 | // ─── Gauge arc math ─────────────────────────────────────────────────────────
2041 | var ARC_LEN = 157; // approx circumference of the half-circle path at r=50
2042 | 
2043 | function scoreToArc(score) {
2044 |   return Math.max(0, Math.min(ARC_LEN, (score / 100) * ARC_LEN));
2045 | }
2046 | 
2047 | function scoreToNeedleAngle(score) {
2048 |   // -90deg (full left) to +90deg (full right)
2049 |   return -90 + (score / 100) * 180;
2050 | }
2051 | 
2052 | function scoreToColor(score) {
2053 |   if (score >= 80) return '#CC0000';
2054 |   if (score >= 65) return '#f8c15c';
2055 |   if (score >= 50) return '#22c55e';
2056 |   return 'rgba(255,255,255,0.35)';
2057 | }
2058 | 
2059 | function scoreToVerdict(score) {
2060 |   if (score >= 85) return { label:'▲ STRONG BULL', col:'#CC0000' };
2061 |   if (score >= 70) return { label:'▲ BULLISH', col:'#f8c15c' };
2062 |   if (score >= 55) return { label:'→ NEUTRAL', col:'rgba(255,255,255,0.45)' };
2063 |   return { label:'▼ CAUTION', col:'#888' };
2064 | }
2065 | 
2066 | function animateGauge(streamId, score) {
2067 |   var color = scoreToColor(score);
2068 |   var arcEl = document.getElementById('ga-' + streamId);
2069 |   var needleEl = document.getElementById('gn-' + streamId);
2070 |   var scoreEl = document.getElementById('gs-' + streamId);
2071 |   var arrEl = document.getElementById('garr-' + streamId);
2072 | 
2073 |   if (!arcEl) return;
2074 | 
2075 |   arcEl.style.stroke = color;
2076 |   arcEl.style.strokeDasharray = scoreToArc(score) + ' ' + ARC_LEN;
2077 | 
2078 |   var angle = scoreToNeedleAngle(score);
2079 |   needleEl.style.transform = 'rotate(' + angle + 'deg)';
2080 |   scoreEl.textContent = score;
2081 |   scoreEl.style.fill = color;
2082 | 
2083 |   var v = scoreToVerdict(score);
2084 |   arrEl.textContent = v.label.split(' ')[0];
2085 |   arrEl.style.color = v.col;
2086 | }
2087 | 
2088 | function updateComposite(allScores) {
2089 |   var vals = Object.values(allScores);
2090 |   if (!vals.length) return;
2091 |   var avg = Math.round(vals.reduce(function(a,b){return a+b;},0)/vals.length);
2092 |   var scoreEl = document.getElementById('ss2-score-num');
2093 |   var verdEl = document.getElementById('ss2-verdict');
2094 |   var v = scoreToVerdict(avg);
2095 |   if (scoreEl) { scoreEl.textContent = avg; scoreEl.style.color = v.col; }
2096 |   if (verdEl) { verdEl.textContent = v.label; verdEl.style.color = v.col; }
2097 |   // Update waterfall heading
2098 |   var wfHead = document.querySelector('#ss2-waterfall .ss2-overline');
2099 |   if (wfHead) wfHead.innerHTML = 'CONVERGENCE WATERFALL &nbsp;<span style="color:rgba(255,255,255,0.2);font-size:6px;">· CONTRIBUTION TO ' + avg + '/100</span>';
2100 |   return avg;
2101 | }
2102 | 
2103 | // ─── API fetches ─────────────────────────────────────────────────────────────
2104 | function fetchAll() {
2105 |   var calls = [
2106 |     fetch('/api/congress/ihx').then(function(r){return r.json();}).then(function(d){ liveData.ihx = d; }),
2107 |     fetch('/api/donations/pulse').then(function(r){return r.json();}).then(function(d){ liveData.pac = d; }),
2108 |     fetch('/api/panopticon/bills').then(function(r){return r.json();}).then(function(d){ liveData.bills = d; }),
2109 |     fetch('/api/orb').then(function(r){return r.json();}).then(function(d){ liveData.orb = d; }),
2110 |     fetch('/api/panopticon/institutional').then(function(r){return r.json();}).then(function(d){ liveData.inst = d; }),
2111 |     fetch('/api/congress/trades').then(function(r){return r.json();}).then(function(d){ liveData.trades = d; }),
2112 |     fetch('/api/panopticon/pe-datastream').then(function(r){return r.json();}).then(function(d){ liveData.pe = d; }),
2113 |   ];
2114 |   Promise.allSettled(calls).then(function() {
2115 |     computeScores();
2116 |     renderAll();
2117 |   });
2118 | }
2119 | 
2120 | function computeScores() {
2121 |   var ihx = liveData.ihx || {};
2122 |   var pac = liveData.pac || {};
2123 |   var bills = liveData.bills || {};
2124 |   var orb = (liveData.orb || {});
2125 |   var inst = liveData.inst || {};
2126 |   var streams = orb.streams || {};
2127 | 
2128 |   // Congress: IHX score is 0-100
2129 |   scores.congress = ihx.score || 64;
2130 | 
2131 |   // PAC: donation pulse score
2132 |   scores.pac = pac.score || 88;
2133 | 
2134 |   // Legislation: weight GENIUS (passed=+25), bill bullish count, bills_with_votes
2135 |   var legBase = 50;
2136 |   var billsWithVotes = bills.bills_with_votes || 0;
2137 |   var bullish = bills.bullish_count || 0;
2138 |   legBase += Math.min(30, billsWithVotes * 6);
2139 |   legBase += Math.min(10, bullish * 5);
2140 |   legBase += 15; // GENIUS Act supermajority permanent bonus
2141 |   scores.legislation = Math.min(100, legBase);
2142 | 
2143 |   // On-chain: blend ORB streams (hashrate, accum, exchange_flow, whale)
2144 |   var hashrate = streams.hashrate || 83;
2145 |   var accum = streams.accum || 65;
2146 |   var exchFlow = streams.exchange_flow || 50;
2147 |   var whale = streams.whale || 90;
2148 |   scores.onchain = Math.round((hashrate * 0.3 + accum * 0.3 + exchFlow * 0.2 + whale * 0.2));
2149 | 
2150 |   // Institutional: filers + coalition signal
2151 |   var filers = inst.total_institutional_filers || 20;
2152 |   var coalition = (inst.coalition_summary || {}).count || 0;
2153 |   scores.institutional = Math.min(100, Math.round(40 + filers * 1.2 + coalition * 0.5));
2154 | 
2155 |   // Geo: macro_corr + polymarket blend from ORB
2156 |   var macro = streams.macro_corr || 69.8;
2157 |   var poly = streams.polymarket || 74;
2158 |   var putcall = streams.put_call || 70;
2159 |   scores.geo = Math.round((macro * 0.4 + poly * 0.3 + putcall * 0.3));
2160 | }
2161 | 
2162 | // ─── Render all elements ─────────────────────────────────────────────────────
2163 | function renderAll() {
2164 |   streamOrder.forEach(function(id) {
2165 |     animateGauge(id, scores[id] || 50);
2166 |     // Update gauge sub-label with live key stat
2167 |     var subEl = document.getElementById('gd-' + id);
2168 |     if (subEl) subEl.textContent = getLiveSubLabel(id);
2169 |   });
2170 |   var avg = updateComposite(scores);
2171 |   renderSignalBoard();
2172 |   renderCorrelationMap();
2173 |   renderWaterfall();
2174 |   document.getElementById('ss2-board-ts').textContent = new Date().toLocaleTimeString() + ' LOCAL';
2175 | }
2176 | 
2177 | function getLiveSubLabel(id) {
2178 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {}, orb = liveData.orb || {};
2179 |   var inst = liveData.inst || {}, bills = liveData.bills || {};
2180 |   var streams = orb.streams || {};
2181 |   switch(id) {
2182 |     case 'congress':     return 'IHX ' + (ihx.score||'—') + ' · ' + (ihx.buy_count||0) + 'B/' + (ihx.sell_count||0) + 'S · ' + (ihx.crypto_trades||0) + ' crypto';
2183 |     case 'pac':          return '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M raised · $' + ((pac.fairshake_spend||0)/1e6).toFixed(1) + 'M spent';
2184 |     case 'legislation':  return (bills.bills_with_votes||0) + ' with votes · GENIUS 66–32';
2185 |     case 'onchain':      return 'HR ' + (streams.hashrate||0) + ' · ACCUM ' + (streams.accum||0) + ' · WHALE ' + (streams.whale||0);
2186 |     case 'institutional':return (inst.total_institutional_filers||0) + ' filers · ' + ((inst.coalition_summary||{}).count||0) + ' coalition';
2187 |     case 'geo':          return 'MACRO ' + Math.round(streams.macro_corr||0) + ' · POLY ' + (streams.polymarket||0) + ' · P/C ' + Math.round(streams.put_call||0);
2188 |   }
2189 |   return '';
2190 | }
2191 | 
2192 | // ─── Data card (expanded on gauge click) ────────────────────────────────────
2193 | var activeGauge = null;
2194 | document.addEventListener('click', function(e) {
2195 |   var cell = e.target.closest('.ss2-gauge-cell');
2196 |   if (cell) {
2197 |     var sid = cell.getAttribute('data-stream');
2198 |     if (activeGauge === sid) {
2199 |       closeCard();
2200 |     } else {
2201 |       openCard(sid, cell);
2202 |     }
2203 |     return;
2204 |   }
2205 |   if (!e.target.closest('#ss2-datacard')) closeCard();
2206 | });
2207 | 
2208 | function closeCard() {
2209 |   var card = document.getElementById('ss2-datacard');
2210 |   card.classList.remove('visible');
2211 |   if (activeGauge) {
2212 |     document.getElementById('gc-' + activeGauge).classList.remove('active');
2213 |   }
2214 |   activeGauge = null;
2215 | }
2216 | 
2217 | function openCard(sid, cell) {
2218 |   if (activeGauge) document.getElementById('gc-' + activeGauge).classList.remove('active');
2219 |   activeGauge = sid;
2220 |   cell.classList.add('active');
2221 | 
2222 |   var card = document.getElementById('ss2-datacard');
2223 |   var score = scores[sid] || 50;
2224 |   var v = scoreToVerdict(score);
2225 | 
2226 |   document.getElementById('ss2-dc-stream').textContent = STREAMS[sid].label + ' STREAM';
2227 |   document.getElementById('ss2-dc-title').textContent = STREAMS[sid].sub;
2228 |   document.getElementById('ss2-dc-score').textContent = score;
2229 |   document.getElementById('ss2-dc-score').style.color = scoreToColor(score);
2230 |   document.getElementById('ss2-dc-verdict').textContent = v.label;
2231 |   document.getElementById('ss2-dc-verdict').style.color = v.col;
2232 | 
2233 |   var rows = getCardRows(sid);
2234 |   var rowsEl = document.getElementById('ss2-dc-rows');
2235 |   rowsEl.innerHTML = rows.map(function(r) {
2236 |     return '<div class="ss2-dc-row"><span class="ss2-dc-key">' + r.k + '</span><span class="ss2-dc-val ' + (r.cls||'') + '">' + r.v + '</span></div>';
2237 |   }).join('');
2238 | 
2239 |   document.getElementById('ss2-dc-insight').textContent = getInsight(sid);
2240 | 
2241 |   // Position card below the clicked gauge row
2242 |   var rect = cell.getBoundingClientRect();
2243 |   var rootRect = document.getElementById('ss2-root').getBoundingClientRect();
2244 |   card.style.top = (rect.bottom - rootRect.top + 8) + 'px';
2245 |   card.classList.add('visible');
2246 | }
2247 | 
2248 | function getCardRows(sid) {
2249 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {}, bills = liveData.bills || {};
2250 |   var orb = liveData.orb || {}, streams = (orb.streams || {}), inst = liveData.inst || {};
2251 |   var pe = liveData.pe || {}, trades = liveData.trades || {};
2252 |   switch(sid) {
2253 |     case 'congress': return [
2254 |       { k:'IHX Score',        v: ihx.score + '/100',                    cls: ihx.score>=70?'green':ihx.score>=50?'gold':'hot' },
2255 |       { k:'Buy / Sell',       v: (ihx.buy_count||0) + ' buys / ' + (ihx.sell_count||0) + ' sells' },
2256 |       { k:'Crypto Trades',    v: (ihx.crypto_trades||0) + ' / 8 total' },
2257 |       { k:'Signal',           v: (ihx.signal||'neutral').toUpperCase() },
2258 |       { k:'Top buy',          v: 'McCormick — Bitwise BTC ETF',         cls:'green' },
2259 |       { k:'Top sell',         v: 'Tim Moore — COIN (2-day filing)',      cls:'hot' },
2260 |       { k:'Conviction peak',  v: '95% — Moore COIN, 80-95% — McCormick' },
2261 |       { k:'Net positioning',  v: ihx.buy_count > ihx.sell_count ? 'BULLISH BIAS' : 'MIXED', cls:'gold' },
2262 |     ];
2263 |     case 'pac': var exps = pac.fairshake_expenditures || []; return [
2264 |       { k:'Fairshake raised',  v: '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M (2026 cycle)', cls:'hot' },
2265 |       { k:'Deployed',          v: '$' + ((pac.fairshake_spend||0)/1e6).toFixed(1) + 'M' },
2266 |       { k:'Pulse score',       v: (pac.score||88) + '/100 ' + (pac.label||'HIGH') },
2267 |       { k:'Crypto PACs',       v: (pac.crypto_committees||0) + ' active committees' },
2268 |       { k:'Top donor',         v: 'a16z (AH Capital) — $23.8M',         cls:'gold' },
2269 |       { k:'#2 donor',          v: 'Ben Horowitz — $11.9M' },
2270 |       { k:'#3 donor',          v: 'Marc Andreessen — $11.9M' },
2271 |       { k:'Biggest OPPOSE',    v: (exps[0] ? (exps[0].candidate||'?').substring(0,28) + ' $' + ((exps[0].amount||0)/1e6).toFixed(1)+'M' : '—'), cls:'hot' },
2272 |     ];
2273 |     case 'legislation': var blist = (bills.bills||[]).filter(function(b){return b.congress_score>50;}).slice(0,4); return [
2274 |       { k:'Bills tracked',     v: ((bills.bills||[]).length || 18) + ' total' },
2275 |       { k:'With floor votes',  v: (bills.bills_with_votes||0) + ' bills' },
2276 |       { k:'GENIUS Act',        v: 'PASSED 66–32 Senate',                 cls:'green' },
2277 |       { k:'Market Clarity',    v: '69% congressional support',           cls:'green' },
2278 |       { k:'Anti-CBDC',         v: 'Introduced — Tom Emmer',              cls:'gold' },
2279 |       { k:'BTC Reserve Act',   v: 'Introduced — Tim Burchett',           cls:'gold' },
2280 |       { k:'STABLE Act',        v: 'Introduced — Bryan Steil' },
2281 |       { k:'Bullish vs bearish',v: (bills.bullish_count||0) + 'B / ' + (bills.bearish_count||0) + 'B gap' },
2282 |     ];
2283 |     case 'onchain': return [
2284 |       { k:'Hashrate signal',   v: (streams.hashrate||0) + '/100',         cls: streams.hashrate>=80?'green':'gold' },
2285 |       { k:'Accumulation',      v: (streams.accum||0) + '/100' },
2286 |       { k:'Exchange flow',     v: (streams.exchange_flow||0) + '/100' },
2287 |       { k:'Whale signal',      v: (streams.whale||0) + '/100',            cls: streams.whale>=80?'green':'gold' },
2288 |       { k:'Fear & Greed',      v: (streams.fear_greed||0) + '/100 (FEAR)',cls: streams.fear_greed<=30?'hot':'' },
2289 |       { k:'Fee signal',        v: (streams.fees||0) + '/100',             cls: streams.fees>=90?'green':'' },
2290 |       { k:'SOPR',              v: '0.15 — capitulation zone',             cls:'hot' },
2291 |       { k:'Puell Multiple',    v: 'Green accumulation band',              cls:'green' },
2292 |     ];
2293 |     case 'institutional': return [
2294 |       { k:'Total 13F filers',  v: (inst.total_institutional_filers||0),  cls:'green' },
2295 |       { k:'Coalition detected',v: ((inst.coalition_summary||{}).count||0) + ' coordinated', cls:'hot' },
2296 |       { k:'PE Form D rounds',  v: (pe.pe_count||0) + ' active raises' },
2297 |       { k:'Top filer',         v: 'ParaFi Capital LP — hedge fund',       cls:'gold' },
2298 |       { k:'#2 filer',          v: 'Avenir Tech Ltd — hedge fund' },
2299 |       { k:'#3 filer',          v: 'Galaxy Institutional Bitcoin Fund' },
2300 |       { k:'Coalition signal',  v: (inst.coalition_summary||{}).detected ? 'ACTIVE — coordinated accumulation' : 'None', cls:(inst.coalition_summary||{}).detected?'hot':'' },
2301 |       { k:'Form 4 insiders',   v: 'Coinbase exec cluster buying',         cls:'green' },
2302 |     ];
2303 |     case 'geo': return [
2304 |       { k:'Macro correlation', v: Math.round(streams.macro_corr||0) + '/100',   cls: streams.macro_corr>=65?'green':'' },
2305 |       { k:'Polymarket signal', v: (streams.polymarket||0) + '/100' },
2306 |       { k:'Put/Call ratio',    v: Math.round(streams.put_call||0) + '/100',      cls:'green' },
2307 |       { k:'US Strategic Res.', v: 'EO 14233 — BTC stockpile active',     cls:'green' },
2308 |       { k:'Fed rate (Apr)',    v: '98.2% NO CHANGE (Polymarket)',          cls:'green' },
2309 |       { k:'10Y Treasury',      v: '3.21%' },
2310 |       { k:'JPY pressure',      v: 'Yen debasement accelerating',          cls:'gold' },
2311 |       { k:'EU MiCA',           v: 'Full implementation — neutral' },
2312 |     ];
2313 |   }
2314 |   return [];
2315 | }
2316 | 
2317 | function getInsight(sid) {
2318 |   var insights = {
2319 |     congress:    'IHX at 64 (neutral) with 6/8 crypto-adjacent. McCormick buying Bitwise BTC ETF at 80-95% conviction while Tim Moore\'s 2-day COIN filing speed signals insider awareness. Net positioning: informed bifurcation between senators and representatives.',
2320 |     pac:         'Fairshake 2026 is the largest crypto political operation in US history. a16z, Horowitz, Andreessen coordinating $134M to reshape the congressional map — primarily opposing anti-crypto incumbents. This capital velocity is unprecedented and structurally bullish for regulatory outcomes.',
2321 |     legislation: 'GENIUS Act passing 66-32 was the first major crypto legislation through the Senate. Digital Asset Market Clarity at 69% support signals bipartisan floor momentum. The regulatory moat is forming faster than previous cycles.',
2322 |     onchain:     'SOPR at 0.15 is a deep loss-realization signal. Historical analogue: sub-0.2 SOPR in Q4 2018 preceded +312% over 18 months. Puell Multiple in green band + ATH hashrate (miners not selling) = smart money accumulation concurrent with retail capitulation.',
2323 |     institutional:'Coalition of 18 institutions with coordinated accumulation windows. Galaxy, ParaFi, Coinbase insiders buying via separate channels. Classic informed money vs uninformed market divergence.',
2324 |     geo:         'US Strategic Bitcoin Reserve (EO 14233) represents sovereign demand. 98.2% Polymarket probability of Fed hold removes tail risk. Yen debasement creates structural Bitcoin demand from Japanese capital. Macro backdrop is the most constructive since 2020.',
2325 |   };
2326 |   return insights[sid] || '';
2327 | }
2328 | 
2329 | // ─── Correlation map (canvas) ────────────────────────────────────────────────
2330 | function renderCorrelationMap() {
2331 |   var canvas = document.getElementById('ss2-map-canvas');
2332 |   if (!canvas) return;
2333 |   var wrap = canvas.parentElement;
2334 |   var W = wrap.clientWidth || 400;
2335 |   var H = Math.max(canvas.clientHeight || 0, 280);
2336 |   canvas.width = W * (window.devicePixelRatio||1);
2337 |   canvas.height = H * (window.devicePixelRatio||1);
2338 |   canvas.style.width = W + 'px';
2339 |   canvas.style.height = H + 'px';
2340 |   var ctx = canvas.getContext('2d');
2341 |   ctx.scale(window.devicePixelRatio||1, window.devicePixelRatio||1);
2342 | 
2343 |   // Background
2344 |   ctx.fillStyle = '#050505';
2345 |   ctx.fillRect(0, 0, W, H);
2346 | 
2347 |   // Grid
2348 |   ctx.strokeStyle = 'rgba(255,255,255,0.04)';
2349 |   ctx.lineWidth = 0.5;
2350 |   for (var x=0; x<=W; x+=W/4) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }
2351 |   for (var y=0; y<=H; y+=H/3) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }
2352 | 
2353 |   // Axes
2354 |   ctx.strokeStyle = 'rgba(255,255,255,0.12)';
2355 |   ctx.lineWidth = 1;
2356 |   ctx.beginPath(); ctx.moveTo(W/2,0); ctx.lineTo(W/2,H); ctx.stroke();
2357 |   ctx.beginPath(); ctx.moveTo(0,H/2); ctx.lineTo(W,H/2); ctx.stroke();
2358 | 
2359 |   // Quadrant labels
2360 |   ctx.fillStyle = 'rgba(255,255,255,0.06)';
2361 |   ctx.font = '9px JetBrains Mono';
2362 |   ctx.textAlign = 'center';
2363 |   ctx.fillText('HIGH STRENGTH', W*0.75, 14);
2364 |   ctx.fillText('GAINING MOMENTUM', W*0.75, 26);
2365 |   ctx.fillText('LOW STRENGTH', W*0.25, 14);
2366 |   ctx.fillText('LOSING MOMENTUM', W*0.25, H-8);
2367 | 
2368 |   // Map each stream to X (direction: 0=bearish, 100=bullish) and Y (strength)
2369 |   // X = derived from signal direction  Y = score
2370 |   var mapData = {
2371 |     congress:     { x: 55, y: scores.congress || 64,  color:'#f8c15c' },
2372 |     pac:          { x: 85, y: scores.pac || 88,        color:'#CC0000' },
2373 |     legislation:  { x: 75, y: scores.legislation || 75,color:'#22c55e' },
2374 |     onchain:      { x: 62, y: scores.onchain || 74,    color:'#f8c15c' },
2375 |     institutional:{ x: 70, y: scores.institutional||70,color:'#22c55e' },
2376 |     geo:          { x: 68, y: scores.geo || 70,        color:'#22c55e' },
2377 |   };
2378 | 
2379 |   streamOrder.forEach(function(sid) {
2380 |     var d = mapData[sid];
2381 |     var px = (d.x / 100) * W;
2382 |     var py = H - (d.y / 100) * H;
2383 |     var r = 10 + (d.y / 100) * 12;
2384 | 
2385 |     // Glow
2386 |     var grd = ctx.createRadialGradient(px, py, 0, px, py, r*2);
2387 |     grd.addColorStop(0, d.color + '40');
2388 |     grd.addColorStop(1, d.color + '00');
2389 |     ctx.beginPath(); ctx.arc(px, py, r*2, 0, Math.PI*2);
2390 |     ctx.fillStyle = grd; ctx.fill();
2391 | 
2392 |     // Circle
2393 |     ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI*2);
2394 |     ctx.fillStyle = d.color + '25';
2395 |     ctx.fill();
2396 |     ctx.strokeStyle = d.color;
2397 |     ctx.lineWidth = 1.5;
2398 |     ctx.stroke();
2399 | 
2400 |     // Score label
2401 |     ctx.fillStyle = '#fff';
2402 |     ctx.font = 'bold 9px JetBrains Mono';
2403 |     ctx.textAlign = 'center';
2404 |     ctx.fillText(d.y, px, py + 3);
2405 | 
2406 |     // Stream label below
2407 |     ctx.fillStyle = 'rgba(255,255,255,0.5)';
2408 |     ctx.font = '6px JetBrains Mono';
2409 |     ctx.fillText(STREAMS[sid].label, px, py + r + 10);
2410 |   });
2411 | 
2412 |   // Hover
2413 |   var tooltip = document.getElementById('ss2-map-tooltip');
2414 |   canvas.onmousemove = function(e) {
2415 |     var rect = canvas.getBoundingClientRect();
2416 |     var mx = e.clientX - rect.left, my = e.clientY - rect.top;
2417 |     var hit = null;
2418 |     streamOrder.forEach(function(sid) {
2419 |       var d = mapData[sid];
2420 |       var px = (d.x / 100) * W;
2421 |       var py = H - (d.y / 100) * H;
2422 |       var r = 10 + (d.y / 100) * 12;
2423 |       if (Math.hypot(mx-px, my-py) < r + 8) hit = { sid:sid, d:d, px:px, py:py };
2424 |     });
2425 |     if (hit) {
2426 |       tooltip.style.opacity = '1';
2427 |       tooltip.style.left = (hit.px + 16) + 'px';
2428 |       tooltip.style.top = (hit.py - 20) + 'px';
2429 |       tooltip.innerHTML = '<div style="color:' + hit.d.color + ';font-size:7px;letter-spacing:.15em;margin-bottom:3px;">' + STREAMS[hit.sid].label + '</div>'
2430 |         + '<div style="font-size:11px;font-weight:700;">' + hit.d.y + '/100</div>'
2431 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.5);margin-top:3px;">' + getLiveSubLabel(hit.sid) + '</div>'
2432 |         + '<div style="font-size:7px;color:rgba(255,255,255,0.3);margin-top:4px;">Click gauge above for full breakdown</div>';
2433 |     } else {
2434 |       tooltip.style.opacity = '0';
2435 |     }
2436 |   };
2437 |   canvas.onmouseleave = function() { tooltip.style.opacity = '0'; };
2438 | }
2439 | 
2440 | // ─── Signal board ────────────────────────────────────────────────────────────
2441 | function renderSignalBoard() {
2442 |   var board = document.getElementById('ss2-signal-board');
2443 |   if (!board) return;
2444 |   var ihx = liveData.ihx || {}, pac = liveData.pac || {};
2445 |   var orb = liveData.orb || {}, streams = orb.streams || {};
2446 |   var inst = liveData.inst || {}, bills = liveData.bills || {};
2447 |   var exps = pac.fairshake_expenditures || [];
2448 | 
2449 |   var items = [
2450 |     // CRITICAL (red)
2451 |     { col:'#CC0000', label:'PAC CAPITAL · CRITICAL', text:'Fairshake PAC raised $' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M — largest crypto political operation in US history', val: '$' + ((pac.fairshake_raised||0)/1e6).toFixed(0) + 'M' },
2452 |     exps[0] ? { col:'#CC0000', label:'FAIRSHAKE · TOP EXPENDITURE', text:exps[0].candidate + ' — ' + (exps[0].support==='O'?'OPPOSE':'SUPPORT'), val: '$' + ((exps[0].amount||0)/1e6).toFixed(1) + 'M' } : null,
2453 |     // SIGNAL (orange)
2454 |     { col:'#f8c15c', label:'ON-CHAIN · SOPR SIGNAL', text:'SOPR at 0.15 — historical capitulation. Prior sub-0.2 episodes: avg +312% over 18 months', val: '0.15' },
2455 |     streams.hashrate >= 80 ? { col:'#f8c15c', label:'ON-CHAIN · HASHRATE', text:'Hashrate signal at ' + streams.hashrate + '/100 — miners holding, not selling into weakness', val: streams.hashrate + '/100' } : null,
2456 |     { col:'#f8c15c', label:'CONGRESS · IHX', text:'Insider Heat Index ' + (ihx.score||64) + '/100 — ' + (ihx.buy_count||0) + ' buys vs ' + (ihx.sell_count||0) + ' sells, ' + (ihx.crypto_trades||0) + ' crypto-adjacent', val: (ihx.score||64) + '/100' },
2457 |     { col:'#22c55e', label:'LEGISLATION · GENIUS ACT', text:'Passed Senate 66–32. Digital Asset Market Clarity at 69% congressional support. Regulatory moat forming.', val: '66–32' },
2458 |     (inst.total_institutional_filers||0) > 15 ? { col:'#22c55e', label:'INSTITUTIONAL · COALITION', text:((inst.coalition_summary||{}).count||0) + ' institutions in coordinated BTC ETF accumulation windows — ' + (inst.total_institutional_filers||0) + ' total 13F filers', val: (inst.total_institutional_filers||0) + ' filers' } : null,
2459 |     streams.whale >= 80 ? { col:'#22c55e', label:'ON-CHAIN · WHALE SIGNAL', text:'Whale accumulation signal at ' + streams.whale + '/100 — on-chain large wallet flows bullish', val: streams.whale + '/100' } : null,
2460 |     // NOTE (dim)
2461 |     { col:'rgba(255,255,255,0.3)', label:'GEO · FED RATE', text:'98.2% Polymarket probability of no rate change in April — macro tail risk removed for current cycle', val: '98.2%' },
2462 |     { col:'rgba(255,255,255,0.3)', label:'GEO · US STRATEGIC RESERVE', text:'Executive Order 14233 establishes national Bitcoin stockpile — sovereign demand signal', val: 'EO 14233' },
2463 |   ].filter(Boolean);
2464 | 
2465 |   board.innerHTML = items.map(function(item) {
2466 |     return '<div class="ss2-signal-item">'
2467 |       + '<div class="ss2-si-dot" style="background:' + item.col + ';box-shadow:0 0 4px ' + item.col + ';"></div>'
2468 |       + '<div class="ss2-si-body">'
2469 |       + '<div class="ss2-si-label" style="color:' + item.col + ';">' + item.label + '</div>'
2470 |       + '<div class="ss2-si-text">' + item.text + '</div>'
2471 |       + '</div>'
2472 |       + '<div class="ss2-si-val" style="color:' + item.col + ';">' + item.val + '</div>'
2473 |       + '</div>';
2474 |   }).join('');
2475 | }
2476 | 
2477 | // ─── Waterfall bars ───────────────────────────────────────────────────────────
2478 | function renderWaterfall() {
2479 |   var el = document.getElementById('ss2-waterfall-bars');
2480 |   if (!el) return;
2481 |   var totalScore = 0;
2482 |   streamOrder.forEach(function(id) { totalScore += (scores[id]||0); });
2483 |   var avg = totalScore / streamOrder.length;
2484 | 
2485 |   el.innerHTML = streamOrder.map(function(sid) {
2486 |     var score = scores[sid] || 50;
2487 |     var color = scoreToColor(score);
2488 |     var contrib = Math.round((score / totalScore) * 100);
2489 |     var pct = (score / 100) * 100;
2490 |     return '<div class="ss2-wf-col" onclick="(function(){var cell=document.getElementById(\'gc-\'+\'' + sid + '\');if(cell)cell.click();})();">'
2491 |       + '<div class="ss2-wf-bar-wrap"><div class="ss2-wf-bar" style="height:' + pct + '%;background:' + color + ';box-shadow:0 0 8px ' + color + '44;"></div></div>'
2492 |       + '<div class="ss2-wf-score" style="color:' + color + ';">' + score + '</div>'
2493 |       + '<div class="ss2-wf-label">' + STREAMS[sid].label + '</div>'
2494 |       + '<div class="ss2-wf-contrib">' + contrib + '% weight</div>'
2495 |       + '</div>';
2496 |   }).join('');
2497 | }
2498 | 
2499 | // ─── Init ────────────────────────────────────────────────────────────────────
2500 | fetchAll();
2501 | setInterval(fetchAll, 120000); // refresh every 2 min
2502 | 
2503 | // Close card when pressing Escape
2504 | document.addEventListener('keydown', function(e) {
2505 |   if (e.key === 'Escape') closeCard();
2506 | });
2507 | 
2508 | })();
2509 | </script>
2510 | 
2511 | 
2512 | <!-- ═══ THREE COLUMN GRID ═══ -->
2513 | <div class="pn-main">
2514 |     <div class="pn-grid">
2515 | 
2516 |         <!-- ═══ COLUMN 1: CONFIRMED DISCLOSURES (FREE in demo) ═══ -->
2517 |         <div class="pn-panel pn-tier-confirmed">
2518 |             <div class="pn-panel-head">
2519 |                 <span class="tier-dot"></span>
2520 |                 <span class="tier-label">TIER 1 — CONFIRMED</span>
2521 |                 <span class="pn-tier-badge tier-1">STOCK ACT</span>
2522 |                 <span class="tier-count">{{ data.disclosures|length }} FILED</span>
2523 |             </div>
2524 | 
2525 |             {% if not demo_mode and data.disclosures_live is defined and not data.disclosures_live %}
2526 |             <div class="pn-fallback-banner">
2527 |                 <strong>HISTORICAL DATA</strong> &mdash; Live data from efts.house.gov temporarily unavailable. Displaying documented public examples from {{ data.fallback_as_of|default('recent filings') }}.
2528 |             </div>
2529 |             {% endif %}
2530 | 
2531 |             <div id="pnDisclosures">
2532 |                 {% for d in data.disclosures %}
2533 |                 <div class="pn-disc-card">
2534 |                     <div class="pn-disc-head">
2535 |                         <div class="pn-disc-entity">{{ d.entity }}</div>
2536 |                         {% if d.party %}
2537 |                         <span class="pn-disc-party {{ d.party }}">{{ d.party }}</span>
2538 |                         {% endif %}
2539 |                     </div>
2540 |                     <div class="pn-disc-fields">
2541 |                         <div>
2542 |                             <div class="pn-disc-field-label">Asset</div>
2543 |                             <div class="pn-disc-field-val">{{ d.asset }}</div>
2544 |                         </div>
2545 |                         <div>
2546 |                             <div class="pn-disc-field-label">Type</div>
2547 |                             <div class="pn-disc-field-val {{ 'buy' if d.trade_type == 'purchase' else 'sell' if d.trade_type == 'sale' else '' }}">{{ d.trade_type|upper }}</div>
2548 |                         </div>
2549 |                         <div>
2550 |                             <div class="pn-disc-field-label">Amount</div>
2551 |                             <div class="pn-disc-field-val">{{ d.amount_range }}</div>
2552 |                         </div>
2553 |                         <div>
2554 |                             <div class="pn-disc-field-label">Filed</div>
2555 |                             <div class="pn-disc-field-val">{{ d.date_filed }}</div>
2556 |                         </div>
2557 |                         {% if d.get('days_to_file') %}
2558 |                         <div>
2559 |                             <div class="pn-disc-field-label">Days to File</div>
2560 |                             <div class="pn-disc-field-val">{{ d.days_to_file }}d</div>
2561 |                         </div>
2562 |                         {% endif %}
2563 |                         {% if d.get('committee') %}
2564 |                         <div>
2565 |                             <div class="pn-disc-field-label">Committee</div>
2566 |                             <div class="pn-disc-field-val">{{ d.committee }}</div>
2567 |                         </div>
2568 |                         {% endif %}
2569 |                     </div>
2570 |                     {% if d.get('conviction') and d.conviction.score > 0 %}
2571 |                     <div class="pn-conviction">
2572 |                         <span class="pn-conviction-label">CONVICTION</span>
2573 |                         <span class="pn-conviction-score {{ d.conviction.color }}">{{ d.conviction.score }}%</span>
2574 |                         <span class="pn-conviction-tag {{ d.conviction.color }}">{{ d.conviction.label }}</span>
2575 |                         <div class="pn-conviction-bar">
2576 |                             <div class="pn-conviction-bar-fill {{ d.conviction.color }}" style="width:{{ d.conviction.score }}%"></div>
2577 |                         </div>
2578 |                     </div>
2579 |                     {% endif %}
2580 |                     {% if d.get('correlation_note') %}
2581 |                     <div class="pn-disc-correlation">{{ d.correlation_note }}</div>
2582 |                     {% endif %}
2583 |                     {% if d.get('status') == 'loading' %}
2584 |                     <div style="margin-top:8px;">
2585 |                         <span class="pn-status-chip loading">Awaiting Live Data</span>
2586 |                     </div>
2587 |                     {% endif %}
2588 |                     <div class="pn-disc-source">
2589 |                         Source: <a href="{{ d.source_url }}" target="_blank" rel="noopener">Public Financial Disclosure</a>
2590 |                     </div>
2591 |                 </div>
2592 |                 {% endfor %}
2593 |                 {% if not data.disclosures %}
2594 |                 <div class="pn-empty">No crypto-related disclosures in current window</div>
2595 |                 {% endif %}
2596 |             </div>
2597 | 
2598 |             <!-- WATCH LIST -->
2599 |             {% if data.watch_list %}
2600 |             <div class="pn-section-label">TIER 3 — WATCH LIST</div>
2601 |             {% for w in data.watch_list %}
2602 |             <div class="pn-watchlist-item">
2603 |                 <div class="pn-watchlist-name">
2604 |                     {{ w.name }}
2605 |                     <span class="pn-disc-party {{ w.party }}" style="margin-left:4px;font-size:8px;">{{ w.party }}</span>
2606 |                 </div>
2607 |                 <div class="pn-watchlist-note">{{ w.note }}</div>
2608 |             </div>
2609 |             {% endfor %}
2610 |             {% endif %}
2611 |         </div>
2612 | 
2613 |         <!-- ═══ COLUMN 2: FLAGGED — PATTERN DETECTION ═══ -->
2614 |         <div class="pn-panel pn-tier-flagged">
2615 |             <div class="pn-panel-head">
2616 |                 <span class="tier-dot"></span>
2617 |                 <span class="tier-label">TIER 2 — FLAGGED</span>
2618 |                 <span class="pn-tier-badge tier-2">PATTERNS</span>
2619 |                 <span class="tier-count">{{ data.flagged|length }} DETECTED</span>
2620 |             </div>
2621 | 
2622 |             {% if demo_mode %}
2623 |             <div class="pn-classified-overlay">
2624 |                 <div class="pn-classified-stamp">CLASSIFIED</div>
2625 |                 <div class="pn-classified-sub">Commander Access Required</div>
2626 |                 <a href="/join" class="pn-upgrade-btn">Unlock Intelligence</a>
2627 |             </div>
2628 |             {% endif %}
2629 | 
2630 |             <div class="pn-disclaimer-note">
2631 |                 PATTERN FOR RESEARCH &mdash; NOT VERIFIED. Statistical correlations shown for independent research purposes only. These are computed patterns, not accusations.
2632 |             </div>
2633 | 
2634 |             <!-- Correlation Timeline SVG -->
2635 |             <div class="pn-section-label">CORRELATION TIMELINE</div>
2636 |             <div id="pnCorrelations">
2637 |                 {% for c in data.correlations %}
2638 |                 <div class="pn-corr-timeline" data-idx="{{ loop.index }}">
2639 |                     <!-- Gap indicator -->
2640 |                     {% set gap = c.get('gap_days', 0) %}
2641 |                     {% set gap_color = 'red' if gap < 7 else ('orange' if gap < 30 else 'white') %}
2642 |                     <div class="pn-corr-gap {{ c.get('gap_color', gap_color) }}">
2643 |                         {% if gap < 7 %}&#9888;{% elif gap < 30 %}&#9679;{% else %}&#9675;{% endif %}
2644 |                         {{ gap }} DAY GAP
2645 |                     </div>
2646 | 
2647 |                     <!-- SVG Timeline: Trade Date → Event Date -->
2648 |                     <svg width="100%" height="90" viewBox="0 0 500 90" preserveAspectRatio="xMidYMid meet">
2649 |                         <!-- Trade node -->
2650 |                         <g class="pn-corr-node" transform="translate(60,40)">
2651 |                             <circle r="10" fill="{{ '#ff3b5f' if gap < 7 else ('#f8c15c' if gap < 30 else '#fff') }}" opacity="0.9"/>
2652 |                             <text y="-16" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">TRADE</text>
2653 |                             <text y="28" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7">{{ c.disclosure.date[:10] if c.disclosure else '' }}</text>
2654 |                         </g>
2655 |                         <!-- Connecting line with gap label -->
2656 |                         <path class="pn-corr-path" d="M70,40 L230,40" stroke="{{ '#ff3b5f' if gap < 7 else ('#f8c15c' if gap < 30 else '#555') }}" stroke-width="2" style="animation-delay:0.2s"/>
2657 |                         <text x="150" y="32" text-anchor="middle" fill="{{ '#ff3b5f' if gap < 7 else '#f8c15c' }}" font-family="JetBrains Mono" font-size="10" font-weight="700">{{ gap }}d</text>
2658 |                         <!-- Event node -->
2659 |                         <g class="pn-corr-node" transform="translate(240,40)">
2660 |                             <circle r="10" fill="#fff" opacity="0.7"/>
2661 |                             <text y="-16" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">EVENT</text>
2662 |                         </g>
2663 |                         <!-- Score -->
2664 |                         <path class="pn-corr-path" d="M250,40 L400,40" stroke="var(--pn-gold)" stroke-width="1.5" style="animation-delay:0.6s"/>
2665 |                         <g class="pn-corr-node" transform="translate(420,40)">
2666 |                             <circle r="14" fill="none" stroke="{{ '#ff3b5f' if c.correlation_score > 0.8 else '#f8c15c' }}" stroke-width="2" opacity="0.8"/>
2667 |                             <text y="4" text-anchor="middle" fill="{{ '#ff3b5f' if c.correlation_score > 0.8 else '#f8c15c' }}" font-family="JetBrains Mono" font-size="10" font-weight="700">{{ "%.0f"|format(c.correlation_score * 100) }}%</text>
2668 |                             <text y="28" text-anchor="middle" fill="#888" font-family="JetBrains Mono" font-size="7" letter-spacing="1">SCORE</text>
2669 |                         </g>
2670 |                     </svg>
2671 | 
2672 |                     <div class="pn-corr-summary">{{ c.timeline_summary }}</div>
2673 | 
2674 |                     <div>
2675 |                         {% if c.disclosure %}
2676 |                         <div class="pn-corr-event-row">
2677 |                             <span class="pn-corr-event-tag disclosure">DISCLOSURE</span>
2678 |                             {{ c.disclosure.entity }} &mdash; {{ c.disclosure.asset }} ({{ c.disclosure.trade_type }})
2679 |                         </div>
2680 |                         {% endif %}
2681 |                         {% for w in c.related_whales %}
2682 |                         <div class="pn-corr-event-row">
2683 |                             <span class="pn-corr-event-tag whale">WHALE</span>
2684 |                             {{ w.entity }} &mdash; {{ w.amount }} {{ w.direction }}
2685 |                         </div>
2686 |                         {% endfor %}
2687 |                         {% for g in c.related_geo %}
2688 |                         <div class="pn-corr-event-row">
2689 |                             <span class="pn-corr-event-tag geo">GEO</span>
2690 |                             {{ g.headline[:80] }}{% if g.headline|length > 80 %}...{% endif %}
2691 |                         </div>
2692 |                         {% endfor %}
2693 |                     </div>
2694 | 
2695 |                     {% if not demo_mode %}
2696 |                     <button class="pn-btc-case-btn" onclick="makeBitcoinCase(this, '{{ c.timeline_summary|e }}')" data-idx="{{ loop.index }}">
2697 |                         &#x20BF; Make the Bitcoin Case
2698 |                     </button>
2699 |                     <div class="pn-btc-case-output" id="btcCase{{ loop.index }}"></div>
2700 |                     {% endif %}
2701 |                 </div>
2702 |                 {% endfor %}
2703 |                 {% if not data.correlations %}
2704 |                 <div class="pn-empty">Awaiting correlated events...</div>
2705 |                 {% endif %}
2706 |             </div>
2707 | 
2708 |             <!-- Flagged Trades -->
2709 |             <div class="pn-section-label">FLAGGED TRADES</div>
2710 |             {% for f in data.flagged %}
2711 |             <div class="pn-disc-card" style="border-left-color:var(--pn-gold);">
2712 |                 <div class="pn-disc-head">
2713 |                     <div class="pn-disc-entity">{{ f.entity }}</div>
2714 |                     {% if f.party %}
2715 |                     <span class="pn-disc-party {{ f.party }}">{{ f.party }}</span>
2716 |                     {% endif %}
2717 |                 </div>
2718 |                 <div class="pn-disc-fields">
2719 |                     <div>
2720 |                         <div class="pn-disc-field-label">Asset</div>
2721 |                         <div class="pn-disc-field-val">{{ f.asset }}</div>
2722 |                     </div>
2723 |                     <div>
2724 |                         <div class="pn-disc-field-label">Score</div>
2725 |                         <div class="pn-disc-field-val" style="color:var(--pn-gold)">{{ "%.0f"|format(f.correlation_score * 100) }}%</div>
2726 |                     </div>
2727 |                 </div>
2728 |                 <div class="pn-disc-correlation" style="border-color:rgba(248,193,92,0.15);color:var(--pn-gold);">{{ f.flag_reason }}</div>
2729 |             </div>
2730 |             {% endfor %}
2731 |             {% if not data.flagged %}
2732 |             <div class="pn-empty">No statistical patterns detected in current window</div>
2733 |             {% endif %}
2734 |         </div>
2735 | 
2736 |         <!-- ═══ COLUMN 3: REAL-TIME FEED (FREE in demo) ═══ -->
2737 |         <div class="pn-panel pn-tier-feed">
2738 |             <div class="pn-panel-head">
2739 |                 <span class="tier-dot"></span>
2740 |                 <span class="tier-label">REAL-TIME FEED</span>
2741 |                 <span class="tier-count">WHALE + MARKET + GEO</span><span style="display:inline-flex;align-items:center;gap:5px;margin-left:10px;"><span id="pnStreamDot" style="width:7px;height:7px;border-radius:50%;background:#888;display:inline-block;"></span><span id="pnStreamLabel" style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.12em;color:#888;">CONNECTING</span></span>
2742 |             </div>
2743 | 
2744 |             <!-- Whale Tracker -->
2745 |             <div class="pn-section-label">WHALE TRACKER</div>
2746 |             <div id="pnWhales">
2747 |                 {% for w in data.whales %}
2748 |                 <div class="pn-whale-item {{ w.tx_type }}">
2749 |                     <div class="pn-whale-row">
2750 |                         <div class="pn-whale-entity">{{ w.entity }}</div>
2751 |                         <span class="pn-whale-type-tag {{ w.tx_type }}">{{ w.tx_type|upper }}</span>
2752 |                         {% if w.get('flow_signal') %}
2753 |                         <span class="pn-whale-signal-tag {{ w.flow_signal }}">{{ w.flow_signal|upper }}</span>
2754 |                         {% endif %}
2755 |                     </div>
2756 |                     <div class="pn-whale-amt {{ w.tx_type }}">
2757 |                         {% if w.tx_type == 'inflow' %}+{% else %}-{% endif %}{{ w.amount_btc }} BTC
2758 |                     </div>
2759 |                     {% if w.amount_usd %}
2760 |                     <div class="pn-whale-usd">${{ "{:,.0f}".format(w.amount_usd) }} USD</div>
2761 |                     {% endif %}
2762 |                     {% if w.get('flow_context') %}
2763 |                     <div class="pn-whale-flow {{ w.flow_signal|default('neutral') }}">
2764 |                         <div class="pn-whale-flow-label">{{ w.flow_label|default('TRANSFER') }}</div>
2765 |                         {{ w.flow_context }}
2766 |                     </div>
2767 |                     {% endif %}
2768 |                     <div class="pn-whale-size-bar" style="width:{{ [w.amount_btc / 10, 100]|min }}%"></div>
2769 |                     <div class="pn-whale-meta">
2770 |                         <span>{{ w.address }}</span>
2771 |                         <a href="{{ w.source_url }}" target="_blank" rel="noopener">View TX &rarr;</a>
2772 |                     </div>
2773 |                 </div>
2774 |                 {% endfor %}
2775 |                 {% if not data.whales %}
2776 |                 <div class="pn-loading">
2777 |                     <div class="pn-loading-dot"></div>
2778 |                     <div class="pn-loading-dot"></div>
2779 |                     <div class="pn-loading-dot"></div>
2780 |                     Scanning whale wallets...
2781 |                 </div>
2782 |                 {% endif %}
2783 |             </div>
2784 | 
2785 |             <!-- Polymarket -->
2786 |             <div class="pn-section-label">BITCOIN PREDICTION MARKETS</div>
2787 |             <div id="pnPolymarket">
2788 |                 {% if data.polymarket %}
2789 |                 <!-- Hero market: highest volume -->
2790 |                 {% set hero = data.polymarket[0] %}
2791 |                 <div class="pn-poly-hero">
2792 |                     {% if hero.get('event_title') %}
2793 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--pn-gold);margin-bottom:6px;">TOP MARKET</div>
2794 |                     {% endif %}
2795 |                     <div class="pn-poly-question">{{ hero.question }}</div>
2796 |                     <div class="pn-poly-row">
2797 |                         {% if hero.yes_price %}
2798 |                         <span class="pn-poly-pct">{{ hero.yes_price }}%</span>
2799 |                         <span class="pn-poly-yes">YES</span>
2800 |                         {% else %}
2801 |                         <span class="pn-poly-pct" style="color:var(--pn-muted)">--</span>
2802 |                         {% endif %}
2803 |                         <span class="pn-poly-signal {{ hero.btc_signal }}">
2804 |                             {% if hero.btc_signal == 'bullish' %}&#9650;{% elif hero.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
2805 |                             {{ hero.btc_signal|upper }}
2806 |                         </span>
2807 |                     </div>
2808 |                     {% if hero.yes_price %}
2809 |                     <div class="pn-poly-hero-bar">
2810 |                         <div class="pn-poly-hero-bar-fill" style="width:{{ hero.yes_price }}%"></div>
2811 |                     </div>
2812 |                     {% endif %}
2813 |                     <div class="pn-poly-meta">
2814 |                         {% if hero.volume %}<span class="pn-poly-vol-badge">${{ "{:,.0f}".format(hero.volume) }} TOTAL VOL</span>{% endif %}
2815 |                         {% if hero.volume_24h %}<span>${{ "{:,.0f}".format(hero.volume_24h) }} 24h</span>{% endif %}
2816 |                         {% if hero.end_date %}<span>Expires {{ hero.end_date[:10] }}</span>{% endif %}
2817 |                         {% if hero.source_url %}<a href="{{ hero.source_url }}" target="_blank" rel="noopener">Polymarket &rarr;</a>{% endif %}
2818 |                     </div>
2819 |                 </div>
2820 | 
2821 |                 <!-- Remaining markets -->
2822 |                 {% for p in data.polymarket[1:] %}
2823 |                 <div class="pn-poly-item">
2824 |                     <div class="pn-poly-question">{{ p.question }}</div>
2825 |                     <div class="pn-poly-row">
2826 |                         {% if p.yes_price %}
2827 |                         <span class="pn-poly-pct">{{ p.yes_price }}%</span>
2828 |                         <span class="pn-poly-yes">YES</span>
2829 |                         {% else %}
2830 |                         <span class="pn-poly-pct" style="color:var(--pn-muted)">--</span>
2831 |                         {% endif %}
2832 |                         <span class="pn-poly-signal {{ p.btc_signal }}">
2833 |                             {% if p.btc_signal == 'bullish' %}&#9650;{% elif p.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
2834 |                             {{ p.btc_signal|upper }}
2835 |                         </span>
2836 |                     </div>
2837 |                     {% if p.yes_price %}
2838 |                     <div class="pn-poly-bar">
2839 |                         <div class="pn-poly-bar-fill {{ p.btc_signal }}" style="width:{{ p.yes_price }}%"></div>
2840 |                     </div>
2841 |                     {% endif %}
2842 |                     <div class="pn-poly-meta">
2843 |                         {% if p.volume %}<span>${{ "{:,.0f}".format(p.volume) }} vol</span>{% endif %}
2844 |                         {% if p.volume_24h %}<span>${{ "{:,.0f}".format(p.volume_24h) }} 24h</span>{% endif %}
2845 |                         {% if p.end_date %}<span>Expires {{ p.end_date[:10] }}</span>{% endif %}
2846 |                         {% if p.source_url %}<a href="{{ p.source_url }}" target="_blank" rel="noopener">Polymarket &rarr;</a>{% endif %}
2847 |                     </div>
2848 |                 </div>
2849 |                 {% endfor %}
2850 |                 {% else %}
2851 |                 <div class="pn-loading">
2852 |                     <div class="pn-loading-dot"></div>
2853 |                     <div class="pn-loading-dot"></div>
2854 |                     <div class="pn-loading-dot"></div>
2855 |                     Fetching prediction markets...
2856 |                 </div>
2857 |                 {% endif %}
2858 |             </div>
2859 | 
2860 |             <!-- Nation-State / Forex -->
2861 |             {% if data.forex %}
2862 |             <div class="pn-section-label">NATION-STATE SIGNALS</div>
2863 |             <div id="pnForex">
2864 |                 {% for f in data.forex %}
2865 |                 <div class="pn-forex-item">
2866 |                     <span class="pn-forex-pair">{{ f.pair }}</span>
2867 |                     {% if f.rate %}<span class="pn-forex-rate">{{ f.rate }}</span>{% endif %}
2868 |                 </div>
2869 |                 {% endfor %}
2870 |             </div>
2871 |             {% endif %}
2872 | 
2873 |             <!-- Geopolitical Feed -->
2874 |             <div class="pn-section-label">GEOPOLITICAL ALERT FEED</div>
2875 |             <div id="pnGeo">
2876 |                 {% for g in data.geopolitical %}
2877 |                 <div class="pn-geo-item">
2878 |                     <div class="pn-geo-headline">{{ g.headline }}</div>
2879 |                     <span class="pn-geo-signal-tag {{ g.btc_signal }}">
2880 |                         {% if g.btc_signal == 'bullish' %}&#9650;{% elif g.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
2881 |                         BTC {{ g.btc_signal|upper }}
2882 |                     </span>
2883 |                     <div class="pn-geo-rationale">{{ g.btc_rationale }}</div>
2884 |                     <div class="pn-geo-meta">
2885 |                         <span>{{ g.source }}</span>
2886 |                         <span>{{ g.timestamp[:10] if g.timestamp else '' }}</span>
2887 |                     </div>
2888 |                 </div>
2889 |                 {% endfor %}
2890 |                 {% if not data.geopolitical %}
2891 |                 <div class="pn-empty">No geopolitical signals in current window</div>
2892 |                 {% endif %}
2893 |             </div>
2894 | 
2895 |             <!-- Political Donation Pulse -->
2896 |             <div class="pn-section-label">POLITICAL DONATION PULSE</div>
2897 |             <div id="pnDonations" style="padding:12px;">
2898 |                 <div style="color:rgba(255,255,255,0.15);font-size:9px;font-family:'JetBrains Mono',monospace;padding:4px 0;">Loading PAC intelligence...</div>
2899 |             <!-- ═══ PRIVATE EQUITY & INSTITUTIONAL INTELLIGENCE ═══ -->
2900 |             <div class="pn-section-label">INSTITUTIONAL ACCUMULATION</div>
2901 |             <div id="pnInstitutional" style="padding:8px 12px;">
2902 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">
2903 |                     Loading institutional data...
2904 |                 </div>
2905 |             </div>
2906 | 
2907 |             <!-- Coalition Detected Banner (hidden until data loads) -->
2908 |             <div id="pnCoalitionBanner" style="display:none;margin:0 12px 8px;padding:10px 14px;
2909 |                 background:rgba(204,0,0,0.1);border:1px solid rgba(204,0,0,0.4);border-radius:6px;">
2910 |                 <div style="display:flex;align-items:center;gap:8px;">
2911 |                     <div style="width:8px;height:8px;border-radius:50%;background:#cc0000;
2912 |                         animation:pn-pulse 1s ease-in-out infinite;flex-shrink:0;"></div>
2913 |                     <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
2914 |                         letter-spacing:.15em;color:#cc0000;font-weight:700;">COALITION SIGNAL DETECTED</div>
2915 |                 </div>
2916 |                 <div id="pnCoalitionNote" style="font-family:'DM Sans',sans-serif;font-size:11px;
2917 |                     color:rgba(255,255,255,0.7);margin-top:6px;line-height:1.5;"></div>
2918 |             </div>
2919 | 
2920 |             <div class="pn-section-label">PRIVATE EQUITY DATASTREAM</div>
2921 |             <div id="pnPEDatastream" style="padding:8px 12px;">
2922 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">
2923 |                     Loading PE fundraising data...
2924 |                 </div>
2925 |             </div>
2926 | 
2927 | 
2928 |             <!-- ═══ BITCOIN BILL GAP TRACKER ═══ -->
2929 |             <div class="pn-section-label" style="display:flex;justify-content:space-between;align-items:center;">
2930 |                 <span>BITCOIN BILL TRACKER</span>
2931 |                 <span style="font-family:'JetBrains Mono',monospace;font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:.08em;">Source: LegiScan · CC BY 4.0</span>
2932 |             </div>
2933 |             <div id="pnBillTracker" style="padding:8px 12px;">
2934 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;font-family:'JetBrains Mono',monospace;">Loading congressional bill data...</div>
2935 |             </div>
2936 | 
2937 |             <!-- Congressional Trading — STOCK Act -->
2938 |             <div class="pn-section-label" style="display:flex;justify-content:space-between;align-items:center;"><span>CONGRESSIONAL STOCK TRADES</span><span id="pnLastUpdate" style="font-family:'JetBrains Mono',monospace;font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:.06em;"></span></div>
2939 |             <div id="pnCongress" style="padding:8px 12px;">
2940 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Loading STOCK Act filings...</div>
2941 |             </div>
2942 | 
2943 |             <!-- Party Breakdown -->
2944 |             <div class="pn-section-label">PARTY TRADING BREAKDOWN</div>
2945 |             <div id="pnPartyBreakdown" style="padding:8px 12px;">
2946 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Analyzing party patterns...</div>
2947 |             </div>
2948 | 
2949 |             <!-- IHX Score -->
2950 |             <div class="pn-section-label">INSIDER HEAT INDEX (IHX)</div>
2951 |             <div id="pnIHX" style="padding:12px;">
2952 |                 <div style="color:rgba(255,255,255,0.15);font-size:10px;">Computing insider heat...</div>
2953 |             </div>
2954 | 
2955 |                     </div>
2956 |                     <div>
2957 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;color:var(--pn-white);" id="donCommittees">--</div>
2958 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--pn-muted);margin-top:4px;">CRYPTO COMMITTEES</div>
2959 |                     </div>
2960 |                     <div>
2961 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;color:var(--pn-gold);" id="donStates">--</div>
2962 |                         <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--pn-muted);margin-top:4px;">STATES ACTIVE</div>
2963 |                     </div>
2964 |                 </div>
2965 |                 <div style="margin-top:12px;text-align:center;">
2966 |                     <span id="donLabel" style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:2px;padding:4px 12px;border:1px solid var(--pn-border);background:rgba(255,59,95,0.04);color:var(--pn-muted);">LOADING</span>
2967 |                 </div>
2968 |             </div>
2969 |         </div>
2970 | 
2971 |     </div>
2972 | </div>
2973 | 
2974 | 
2975 | 
2976 | 
2977 | <!-- ═══ HISTORICAL PRECEDENTS TIMELINE (GLASSMORPHIC) ═══ -->
2978 | <div class="pn-history">
2979 |     <div class="pn-history-header">HISTORICAL PRECEDENTS</div>
2980 |     <div class="pn-history-subhead">Documented cases of government financial overreach — the pattern Bitcoin was engineered to break.</div>
2981 | 
2982 |     <div class="pn-timeline-scroll">
2983 |         <div class="pn-timeline" id="pn-timeline">
2984 | 
2985 |             <!-- 1: 60 AD — Roman Coin Debasement (ABOVE) -->
2986 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
2987 |                 <div class="pn-tl-year">60 AD</div>
2988 |                 <div class="pn-tl-name">Roman Coin Debasement</div>
2989 |                 <div class="pn-tl-stem"></div>
2990 |                 <div class="pn-tl-dot" data-evt="0" onclick="tlToggle(this)"></div>
2991 |             </div>
2992 | 
2993 |             <!-- 2: 1544 — Henry VIII (BELOW) -->
2994 |             <div class="pn-tl-node tl-below" style="margin-right:40px">
2995 |                 <div class="pn-tl-dot" data-evt="1" onclick="tlToggle(this)"></div>
2996 |                 <div class="pn-tl-stem"></div>
2997 |                 <div class="pn-tl-year">1544</div>
2998 |                 <div class="pn-tl-name">Henry VIII Great Debasement</div>
2999 |             </div>
3000 | 
3001 |             <!-- 3: 1789 — French Assignats (ABOVE) -->
3002 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3003 |                 <div class="pn-tl-year">1789</div>
3004 |                 <div class="pn-tl-name">French Assignat Hyperinflation</div>
3005 |                 <div class="pn-tl-stem"></div>
3006 |                 <div class="pn-tl-dot" data-evt="2" onclick="tlToggle(this)"></div>
3007 |             </div>
3008 | 
3009 |             <!-- 4: 1921 — Weimar (BELOW) -->
3010 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3011 |                 <div class="pn-tl-dot" data-evt="3" onclick="tlToggle(this)"></div>
3012 |                 <div class="pn-tl-stem"></div>
3013 |                 <div class="pn-tl-year">1921</div>
3014 |                 <div class="pn-tl-name">Weimar Hyperinflation</div>
3015 |             </div>
3016 | 
3017 |             <!-- 5: 1933 — FDR Gold Seizure (ABOVE) -->
3018 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3019 |                 <div class="pn-tl-year">1933</div>
3020 |                 <div class="pn-tl-name">FDR Gold Seizure</div>
3021 |                 <div class="pn-tl-stem"></div>
3022 |                 <div class="pn-tl-dot" data-evt="4" onclick="tlToggle(this)"></div>
3023 |             </div>
3024 | 
3025 |             <!-- 6: 1944 — Bretton Woods (BELOW) -->
3026 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3027 |                 <div class="pn-tl-dot" data-evt="5" onclick="tlToggle(this)"></div>
3028 |                 <div class="pn-tl-stem"></div>
3029 |                 <div class="pn-tl-year">1944</div>
3030 |                 <div class="pn-tl-name">Bretton Woods Dollar Peg</div>
3031 |             </div>
3032 | 
3033 |             <!-- 7: 1946 — Hungary (ABOVE) -->
3034 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3035 |                 <div class="pn-tl-year">1946</div>
3036 |                 <div class="pn-tl-name">Hungarian Hyperinflation</div>
3037 |                 <div class="pn-tl-stem"></div>
3038 |                 <div class="pn-tl-dot" data-evt="6" onclick="tlToggle(this)"></div>
3039 |             </div>
3040 | 
3041 |             <!-- 8: 1971 — Nixon Shock (BELOW) -->
3042 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3043 |                 <div class="pn-tl-dot" data-evt="7" onclick="tlToggle(this)"></div>
3044 |                 <div class="pn-tl-stem"></div>
3045 |                 <div class="pn-tl-year">1971</div>
3046 |                 <div class="pn-tl-name">Nixon Shock</div>
3047 |             </div>
3048 | 
3049 |             <!-- 9: 1980s — S&L Crisis (ABOVE) -->
3050 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3051 |                 <div class="pn-tl-year">1980s</div>
3052 |                 <div class="pn-tl-name">S&amp;L Crisis</div>
3053 |                 <div class="pn-tl-stem"></div>
3054 |                 <div class="pn-tl-dot" data-evt="8" onclick="tlToggle(this)"></div>
3055 |             </div>
3056 | 
3057 |             <!-- 10: 2001 — Argentina (BELOW) -->
3058 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3059 |                 <div class="pn-tl-dot" data-evt="9" onclick="tlToggle(this)"></div>
3060 |                 <div class="pn-tl-stem"></div>
3061 |                 <div class="pn-tl-year">2001</div>
3062 |                 <div class="pn-tl-name">Argentina Corralito</div>
3063 |             </div>
3064 | 
3065 |             <!-- 11: 2008 — GFC Bailouts (ABOVE) -->
3066 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3067 |                 <div class="pn-tl-year">2008</div>
3068 |                 <div class="pn-tl-name">Global Financial Crisis</div>
3069 |                 <div class="pn-tl-stem"></div>
3070 |                 <div class="pn-tl-dot" data-evt="10" onclick="tlToggle(this)"></div>
3071 |             </div>
3072 | 
3073 |             <!-- 12: 2013 — Cyprus (BELOW) -->
3074 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3075 |                 <div class="pn-tl-dot" data-evt="11" onclick="tlToggle(this)"></div>
3076 |                 <div class="pn-tl-stem"></div>
3077 |                 <div class="pn-tl-year">2013</div>
3078 |                 <div class="pn-tl-name">Cyprus Bail-In</div>
3079 |             </div>
3080 | 
3081 |             <!-- 13: 2016 — India (ABOVE) -->
3082 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3083 |                 <div class="pn-tl-year">2016</div>
3084 |                 <div class="pn-tl-name">India Demonetization</div>
3085 |                 <div class="pn-tl-stem"></div>
3086 |                 <div class="pn-tl-dot" data-evt="12" onclick="tlToggle(this)"></div>
3087 |             </div>
3088 | 
3089 |             <!-- 14: 2020 — COVID (BELOW) -->
3090 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3091 |                 <div class="pn-tl-dot" data-evt="13" onclick="tlToggle(this)"></div>
3092 |                 <div class="pn-tl-stem"></div>
3093 |                 <div class="pn-tl-year">2020</div>
3094 |                 <div class="pn-tl-name">COVID Money Printing</div>
3095 |             </div>
3096 | 
3097 |             <!-- 15: 2022 — Russia SWIFT (ABOVE) -->
3098 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3099 |                 <div class="pn-tl-year">2022</div>
3100 |                 <div class="pn-tl-name">Russia SWIFT Exclusion</div>
3101 |                 <div class="pn-tl-stem"></div>
3102 |                 <div class="pn-tl-dot" data-evt="14" onclick="tlToggle(this)"></div>
3103 |             </div>
3104 | 
3105 |             <!-- 16: 2022 — Canada Truckers (BELOW) -->
3106 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3107 |                 <div class="pn-tl-dot" data-evt="15" onclick="tlToggle(this)"></div>
3108 |                 <div class="pn-tl-stem"></div>
3109 |                 <div class="pn-tl-year">2022</div>
3110 |                 <div class="pn-tl-name">Canada Trucker Freeze</div>
3111 |             </div>
3112 | 
3113 |             <!-- 17: 2023 — US Banking (ABOVE) -->
3114 |             <div class="pn-tl-node tl-above" style="margin-right:20px">
3115 |                 <div class="pn-tl-year">2023</div>
3116 |                 <div class="pn-tl-name">U.S. Banking Crisis</div>
3117 |                 <div class="pn-tl-stem"></div>
3118 |                 <div class="pn-tl-dot" data-evt="16" onclick="tlToggle(this)"></div>
3119 |             </div>
3120 | 
3121 |             <!-- 18: NOW — CBDC (BELOW) -->
3122 |             <div class="pn-tl-node tl-below" style="margin-right:20px">
3123 |                 <div class="pn-tl-dot" data-evt="17" onclick="tlToggle(this)"></div>
3124 |                 <div class="pn-tl-stem"></div>
3125 |                 <div class="pn-tl-year">NOW</div>
3126 |                 <div class="pn-tl-name">CBDC Push</div>
3127 |             </div>
3128 | 
3129 |         </div>
3130 |     </div>
3131 | 
3132 |     <div class="pn-history-coda">
3133 |         WHY HISTORY MATTERS — These are not conspiracy theories. These are documented events. Bitcoin was built to prevent them.
3134 |     </div>
3135 | </div>
3136 | 
3137 | <!-- Glassmorphic info card (single, repositioned on click) -->
3138 | <div class="pn-tl-card" id="pn-tl-card">
3139 |     <button class="pn-tl-card-close" onclick="tlClose()">&times;</button>
3140 |     <div class="pn-tl-card-header" id="tlCardHeader"></div>
3141 |     <div class="pn-tl-card-short" id="tlCardShort"></div>
3142 |     <div class="pn-tl-card-detail" id="tlCardDetail"></div>
3143 |     <div class="pn-tl-card-btc" id="tlCardBtc"></div>
3144 | </div>
3145 | 
3146 | <script>
3147 | (function(){
3148 | var TL_EVENTS=[
3149 | {year:"60 AD",title:"Roman Coin Debasement",short:"Nero reduces silver content from 90% to near 0% over centuries. Denarius becomes copper-clad.",detail:"Roman emperors starting with Nero systematically reduced silver content in the denarius from ~90% to under 5% to fund wars and government spending. By the Crisis of the Third Century (235\u2013284 AD), 26 emperors ruled in 49 years as the currency collapsed and hyperinflation took hold. The pattern: spend beyond means, debase the money, watch civilization fracture.",btc:"\u26a1 BITCOIN PARALLEL: 21 million coins. No emperor can change that."},
3150 | {year:"1544",title:"Henry VIII Great Debasement",short:"England\u2019s king secretly reduces gold/silver in coins to fund wars. Coins dubbed \u2018Old Coppernose.\u2019",detail:"King Henry VIII reduced gold content from 23 to 20 karat and silver content to just 25% (rest copper) to fund wars with France and Scotland and his lifestyle. Citizens noticed when the copper showed through the silver on the king\u2019s portrait \u2014 the nose turned copper first. Result: Severe inflation, erosion of trust, economic damage lasting decades until reversed by Elizabeth I in 1560.",btc:"\u26a1 BITCOIN PARALLEL: Cryptographically verified. No hidden copper."},
3151 | {year:"1789",title:"French Assignat Hyperinflation",short:"Revolutionary France prints paper money backed by seized church land. Massive over-issue destroys savings.",detail:"The revolutionary government issued paper \u2018assignats\u2019 backed by confiscated church lands, then printed them without restraint to fund wars and deficits. Total issuance: 45 billion livres. Result: Hyperinflation wiped out the middle class, triggered food riots, and contributed to the Reign of Terror. The paper money became so worthless it was burned for heat.",btc:"\u26a1 BITCOIN PARALLEL: Cannot be printed. Supply is fixed at genesis."},
3152 | {year:"1921",title:"Weimar Republic Hyperinflation",short:"Germany prints trillions of marks to pay WWI reparations. A loaf of bread costs 200 billion marks by 1923.",detail:"The German government printed money to pay WWI war reparations imposed by the Treaty of Versailles. By November 1923, a single loaf of bread cost 200 billion marks. Citizens carried cash in wheelbarrows. Middle-class savings were completely destroyed. The resulting economic chaos and resentment directly enabled the rise of extremism. The Reichsbank printed notes so fast new denominations were issued daily.",btc:"\u26a1 BITCOIN PARALLEL: No central bank. No war reparations. 21 million."},
3153 | {year:"1933",title:"FDR Gold Seizure",short:"Executive Order 6102 forces citizens to surrender gold. Penalty: 10 years prison or $10,000 fine.",detail:"President Roosevelt signed Executive Order 6102 requiring all U.S. persons to deliver their gold coins, bullion, and certificates to Federal Reserve banks at $20.67/oz. Days later, the government revalued gold to $35/oz \u2014 an immediate 41% wealth transfer from citizens to the state. Noncompliance carried criminal penalties of up to 10 years imprisonment. This was not a purchase \u2014 it was confiscation.",btc:"\u26a1 BITCOIN PARALLEL: Stored in your head as 12 words. No EO can seize a seed phrase."},
3154 | {year:"1944",title:"Bretton Woods Dollar Peg",short:"USD becomes global reserve currency backed by gold. Seeds Nixon Shock 27 years later.",detail:"44 nations signed the Bretton Woods Agreement making the USD the world reserve currency pegged at $35/oz gold. The U.S. promised to maintain convertibility. For 27 years, the system worked \u2014 until the U.S. printed more dollars than it had gold to back them, setting the stage for Nixon\u2019s 1971 unilateral break.",btc:"\u26a1 BITCOIN PARALLEL: No central peg. No promise of convertibility. It just works."},
3155 | {year:"1946",title:"Hungarian Hyperinflation",short:"Worst hyperinflation in recorded history. Prices doubled every 15 hours. Currency abandoned entirely.",detail:"Post-WWII Hungary experienced the most extreme hyperinflation ever recorded. The Hungarian peng\u0151 lost all value \u2014 at peak, prices doubled every 15.6 hours. The government printed a 100 quintillion peng\u0151 note. Total currency abandoned. A new currency (forint) was introduced, but savings were destroyed absolutely. Workers were paid daily and ran to spend before prices doubled again.",btc:"\u26a1 BITCOIN PARALLEL: Cannot be inflated. Ever."},
3156 | {year:"1971",title:"Nixon Shock",short:"Nixon ends gold convertibility \u2018temporarily.\u2019 54 years later, still temporary.",detail:"On August 15, 1971, President Nixon unilaterally terminated USD convertibility to gold, ending the Bretton Woods system. He called it \u2018temporary.\u2019 Every dollar since has been backed only by government debt. The result: USD has lost 85%+ of its purchasing power since 1971. The move enabled unlimited government spending backed by nothing but future tax obligations and the threat of military force.",btc:"\u26a1 BITCOIN PARALLEL: Born the day Satoshi embedded the bank bailout headline in the genesis block."},
3157 | {year:"1980s",title:"U.S. Savings & Loan Crisis",short:"1,000+ S&Ls fail after deregulation. $160 billion taxpayer bailout. First major \u2018too big to fail.\u2019",detail:"Deregulation of the savings and loan industry combined with government-backed deposit insurance led to reckless lending and outright fraud at over 1,000 institutions. When they failed, taxpayers were forced to cover losses of $124\u2013160 billion. The S&L crisis established the template: privatize profits, socialize losses. Executives faced minimal consequences.",btc:"\u26a1 BITCOIN PARALLEL: No deposit insurance needed. Not your keys, not your coins \u2014 but if it is your keys, no bailout required."},
3158 | {year:"2001",title:"Argentina Corralito",short:"Bank accounts frozen. USD deposits forcibly converted to devalued pesos. Riots in the streets.",detail:"After pegging the peso to the USD, Argentina\u2019s government froze all bank accounts (the \u2018corralito\u2019) limiting withdrawals to $250/week. When the peg broke, USD deposits were forcibly converted to pesos at a rate that immediately lost 70% of value \u2014 wiping out savings overnight. Multiple presidents resigned in weeks. Riots killed dozens. Argentina defaulted on $100 billion in debt.",btc:"\u26a1 BITCOIN PARALLEL: Your wallet. Your keys. No bank holiday can freeze a UTXO."},
3159 | {year:"2008",title:"Global Financial Crisis Bailouts",short:"TARP: $700B. Total Fed backstop: $29 trillion. Banks rescued. Homeowners foreclosed.",detail:"The U.S. government passed TARP ($700B+) and the Federal Reserve provided up to $29 trillion in emergency backstops to rescue banks, AIG, Fannie Mae, Freddie Mac, and the auto industry after the subprime mortgage collapse. While institutions deemed \u2018too big to fail\u2019 were rescued, 10 million Americans lost their homes to foreclosure. The genesis block of Bitcoin was mined January 3, 2009 \u2014 with a newspaper headline about bank bailouts embedded as a timestamp.",btc:"\u26a1 BITCOIN PARALLEL: The genesis block timestamp: \u2018Chancellor on brink of second bailout for banks.\u2019 Satoshi saw this coming."},
3160 | {year:"2013",title:"Cyprus Bail-In",short:"EU forces haircut of 47.5% on deposits over \u20ac100,000. First direct bank account confiscation in modern Europe.",detail:"The European Union forced Cyprus to impose a \u2018bail-in\u2019 as a condition of a \u20ac10B rescue \u2014 directly seizing up to 47.5% of bank deposits over \u20ac100,000. This was the first time in modern history that EU governments explicitly took depositor money to rescue a bank. It established the legal template that deposits are not cash \u2014 they are unsecured loans to the bank.",btc:"\u26a1 BITCOIN PARALLEL: People who held BTC were not subject to the bail-in."},
3161 | {year:"2016",title:"India Demonetization",short:"86% of all currency invalidated overnight. Chaos, queues, economic disruption. Affected 1.3 billion people.",detail:"Indian Prime Minister Modi announced with 4 hours notice that \u20b9500 and \u20b91,000 notes \u2014 86% of all currency in circulation \u2014 were immediately invalid. Citizens had weeks to exchange limited amounts. Result: Cash chaos, severe disruption to the informal economy (which employs 90% of Indians), GDP growth slowed, and the stated goal of eliminating \u2018black money\u2019 largely failed. The demonetization affected 1.3 billion people with near-zero time to prepare.",btc:"\u26a1 BITCOIN PARALLEL: A Bitcoin private key cannot be demonetized by government decree."},
3162 | {year:"2020",title:"COVID Money Printing",short:"$5\u20136 trillion U.S. stimulus + Fed balance sheet to $9T. Highest inflation in 40 years follows.",detail:"The U.S. government passed ~$5\u20136 trillion in fiscal stimulus packages (CARES Act, American Rescue Plan, etc.) while the Federal Reserve doubled its balance sheet from $4T to $9T through quantitative easing. The result: 9.1% inflation in June 2022 \u2014 the highest in 40 years. Purchasing power of savings eroded. Asset owners saw portfolios surge while wage earners fell behind. The Cantillon effect: those closest to the money printer benefit first.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin supply did not change. 21 million. The halving in May 2020 reduced new issuance. Bitcoiners called it."},
3163 | {year:"2022",title:"Russia SWIFT Exclusion",short:"$300B in sovereign reserves frozen. Proof that nation-state assets are weapons.",detail:"Following Russia\u2019s invasion of Ukraine, Western nations froze approximately $300 billion in Russian central bank reserves held in Western financial institutions. This demonstrated that sovereign wealth \u2014 money a country legally owns \u2014 can be weaponized by adversaries with institutional access. No court order, no due process. Every central bank in the world took note.",btc:"\u26a1 BITCOIN PARALLEL: Censorship-resistant by design. No counterparty holds your sats."},
3164 | {year:"2022",title:"Canada Trucker Freeze",short:"Bank accounts frozen without court order. Protesters financially silenced in 48 hours.",detail:"The Canadian government invoked the Emergencies Act to freeze bank accounts of Freedom Convoy protesters and donors without court orders. Financial institutions were directed to freeze accounts based on government lists. Accounts were blocked within 48 hours of the declaration. A peaceful protest was financially neutralized. The act was later found to have been applied unlawfully by a Federal Court, but the damage was done.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin transactions cannot be stopped. A node in your home means no one can freeze your economic activity."},
3165 | {year:"2023",title:"U.S. Banking Crisis",short:"SVB, Signature, Silvergate collapse. Crypto-friendly banks systematically shut down \u2014 Operation Chokepoint 2.0.",detail:"Silicon Valley Bank ($212B), Signature Bank ($110B), and Silvergate Bank collapsed in rapid succession. SVB\u2019s failure was partly triggered by the Fed\u2019s rate hiking cycle destroying its bond portfolio. Signature and Silvergate \u2014 both crypto-friendly banks \u2014 were also shut down by regulators. Critics and a Congressional investigation documented \u2018Operation Chokepoint 2.0\u2019: a coordinated effort to deny banking services to crypto businesses.",btc:"\u26a1 BITCOIN PARALLEL: A bank that cannot be closed. Runs 24/7/365. No bank holiday."},
3166 | {year:"NOW",title:"CBDC Push",short:"130+ countries developing programmable digital currencies. Expiry dates. Spending restrictions. Surveillance.",detail:"As of 2026, 130+ countries (representing 98% of global GDP) are developing or piloting Central Bank Digital Currencies. Unlike cash, CBDCs are programmable: governments can set expiry dates (spend it or lose it), restrict what categories of goods can be purchased, tie spending to social credit scores, and surveil every transaction in real time. China\u2019s digital yuan has already been deployed with regional spending restrictions.",btc:"\u26a1 BITCOIN PARALLEL: Bitcoin is the opt-out. Permissionless. Unseizable. 21 million. Forever."}
3167 | ];
3168 | var openDot=null,card=document.getElementById('pn-tl-card');
3169 | function tlToggle(dot){
3170 |     var idx=parseInt(dot.dataset.evt),e=TL_EVENTS[idx];
3171 |     if(openDot===dot){tlClose();return;}
3172 |     if(openDot)openDot.classList.remove('active');
3173 |     dot.classList.add('active');
3174 |     openDot=dot;
3175 |     document.getElementById('tlCardHeader').textContent=e.year+' \u2014 '+e.title;
3176 |     document.getElementById('tlCardShort').textContent=e.short;
3177 |     document.getElementById('tlCardDetail').textContent=e.detail;
3178 |     document.getElementById('tlCardBtc').textContent=e.btc;
3179 |     /* Position card near the dot */
3180 |     var r=dot.getBoundingClientRect(),cw=340;
3181 |     card.style.visibility='hidden';card.style.display='block';
3182 |     var ch=card.offsetHeight||300;
3183 |     card.style.visibility='';card.style.display='';
3184 |     var left=r.left+r.width/2-cw/2;
3185 |     var top=r.top+window.scrollY-ch-16;
3186 |     if(dot.closest('.tl-below'))top=r.bottom+window.scrollY+12;
3187 |     if(left<8)left=8;
3188 |     if(left+cw>window.innerWidth-8)left=window.innerWidth-cw-8;
3189 |     if(top<8)top=r.bottom+window.scrollY+12;
3190 |     card.style.left=left+'px';card.style.top=top+'px';
3191 |     card.classList.add('active');
3192 | }
3193 | function tlClose(){
3194 |     card.classList.remove('active');
3195 |     if(openDot){openDot.classList.remove('active');openDot=null;}
3196 | }
3197 | window.tlToggle=tlToggle;window.tlClose=tlClose;
3198 | /* Close on click outside */
3199 | document.addEventListener('click',function(ev){
3200 |     if(!ev.target.closest('.pn-tl-dot')&&!ev.target.closest('.pn-tl-card'))tlClose();
3201 | });
3202 | /* Close on scroll */
3203 | var scr=document.querySelector('.pn-timeline-scroll');
3204 | if(scr)scr.addEventListener('scroll',tlClose);
3205 | })();
3206 | </script>
3207 | 
3208 | <!-- ═══ DISCLAIMER ═══ -->
3209 | <div class="pn-disclaimer">
3210 |     All data sourced from public filings (STOCK Act, SEC EDGAR), public blockchain explorers (mempool.space), and open APIs.
3211 |     Correlation shown for independent research purposes only. Protocol Pulse does not make accusations of insider trading.
3212 |     "FLAGGED" items are statistical patterns, not verified misconduct. Always consult original sources.
3213 |     <strong>This is not financial, investment, or legal advice.</strong> Nothing on this dashboard constitutes a recommendation to buy, sell, or hold any asset.
3214 |     All information is provided for educational and research purposes only.
3215 | </div>
3216 | 
3217 | {% endblock %}
3218 | 
3219 | {% block scripts %}
3220 | <script>
3221 | (function() {
3222 |     // ── UTC Clock ──
3223 |     function updateClock() {
3224 |         var now = new Date();
3225 |         var h = String(now.getUTCHours()).padStart(2, '0');
3226 |         var m = String(now.getUTCMinutes()).padStart(2, '0');
3227 |         var s = String(now.getUTCSeconds()).padStart(2, '0');
3228 |         var el = document.getElementById('pnClock');
3229 |         if (el) el.textContent = h + ':' + m + ':' + s + ' UTC';
3230 |     }
3231 |     updateClock();
3232 |     setInterval(updateClock, 1000);
3233 | 
3234 |     // ── Whale Tracker: fetch from /api/orb (works for all users) ──
3235 |     (function() {
3236 |         var el = document.getElementById('pnWhales');
3237 |         if (!el) return;
3238 |         function loadWhales() {
3239 |             fetch('/api/orb')
3240 |                 .then(function(r) { return r.json(); })
3241 |                 .then(function(d) {
3242 |                     var raw = d.raw || {};
3243 |                     var whales = raw.whale_alerts_list || [];
3244 |                     if (!whales.length) {
3245 |                         el.innerHTML = '<div class="pn-empty">No whale activity detected</div>';
3246 |                         return;
3247 |                     }
3248 |                     var html = '';
3249 |                     whales.slice(0, 5).forEach(function(w) {
3250 |                         var tierCol = w.tier === 'CRITICAL' ? '#ef4444' : (w.tier === 'WARNING' ? '#f97316' : 'var(--pn-muted)');
3251 |                         var isInflow = (w.message || '').toLowerCase().indexOf('inflow') >= 0;
3252 |                         var flowClass = isInflow ? 'inflow' : 'outflow';
3253 |                         html += '<div class="pn-whale-item ' + flowClass + '">';
3254 |                         html += '<div class="pn-whale-row">';
3255 |                         html += '<div class="pn-whale-entity" style="color:' + tierCol + ';font-weight:700;font-size:9px;letter-spacing:1px;">' + (w.tier || 'NOTE') + '</div>';
3256 |                         html += '</div>';
3257 |                         html += '<div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">' + (w.message || '') + '</div>';
3258 |                         html += '<div class="pn-whale-meta"><span style="color:var(--pn-muted);font-size:10px;">Score: ' + (w.score || 0) + '</span></div>';
3259 |                         html += '</div>';
3260 |                     });
3261 |                     el.innerHTML = html;
3262 |                     var c = document.getElementById('pnStatWhales');
3263 |                     if (c) c.textContent = whales.length;
3264 |                 })
3265 |                 .catch(function() {});
3266 |         }
3267 |         loadWhales();
3268 |         setInterval(loadWhales, 60000);
3269 |     })();
3270 | 
3271 |     // ── Political Donation Pulse (rebuilt) ──
3272 |     (function() {
3273 |         fetch('/api/donations/pulse')
3274 |             .then(function(r) { return r.json(); })
3275 |             .then(function(d) {
3276 |                 var el = document.getElementById('pnDonations');
3277 |                 if (!el) return;
3278 | 
3279 |                 var score    = d.score || 0;
3280 |                 var label    = d.label || 'LOW';
3281 |                 var spend    = d.fairshake_spend || 0;
3282 |                 var nComm    = d.crypto_committees || 0;
3283 |                 var nStates  = d.states_active || 0;
3284 |                 var exps     = d.fairshake_expenditures || [];
3285 |                 var topDons  = d.top_donations || [];
3286 |                 var scoreCol = score > 70 ? '#CC0000' : score > 40 ? '#f8c15c' : 'rgba(255,255,255,0.3)';
3287 |                 var spendFmt = spend >= 1e6 ? '$' + (spend/1e6).toFixed(1) + 'M'
3288 |                              : spend >= 1e3 ? '$' + (spend/1e3).toFixed(0) + 'K' : '$0';
3289 | 
3290 |                 var html = '<div style="display:flex;gap:12px;margin-bottom:10px;align-items:flex-start;">';
3291 | 
3292 |                 // Pulse score
3293 |                 html += '<div style="text-align:center;min-width:64px;">'
3294 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:28px;font-weight:900;color:' + scoreCol + ';">' + score + '</div>'
3295 |                       + '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.3);margin-top:2px;">PULSE SCORE</div>'
3296 |                       + '</div>';
3297 | 
3298 |                 // Stats
3299 |                 html += '<div style="display:flex;flex-direction:column;gap:6px;flex:1;">';
3300 |                 html += '<div style="display:flex;gap:16px;">';
3301 |                 html += '<div style="text-align:center;">'
3302 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:#f8c15c;">' + spendFmt + '</div>'
3303 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">FAIRSHAKE SPEND</div>'
3304 |                       + '</div>';
3305 |                 html += '<div style="text-align:center;">'
3306 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:rgba(255,255,255,0.7);">' + nComm + '</div>'
3307 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">CRYPTO PACs</div>'
3308 |                       + '</div>';
3309 |                 html += '<div style="text-align:center;">'
3310 |                       + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;font-weight:700;color:rgba(255,255,255,0.7);">' + nStates + '</div>'
3311 |                       + '<div style="font-size:7px;letter-spacing:.08em;color:rgba(255,255,255,0.3);">STATES ACTIVE</div>'
3312 |                       + '</div>';
3313 |                 html += '</div>'; // stats row
3314 |                 html += '</div></div>'; // right col + header
3315 | 
3316 |                 // Fairshake expenditures
3317 |                 if (exps.length) {
3318 |                     html += '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.25);margin-bottom:4px;">FAIRSHAKE PAC — INDEPENDENT EXPENDITURES</div>';
3319 |                     exps.slice(0,4).forEach(function(e) {
3320 |                         var amtFmt = e.amount >= 1e6 ? '$'+(e.amount/1e6).toFixed(1)+'M'
3321 |                                    : e.amount >= 1e3 ? '$'+(e.amount/1e3).toFixed(0)+'K'
3322 |                                    : '$'+e.amount;
3323 |                         var suppCol = e.support === 'S' ? '#22c55e' : '#ef4444';
3324 |                         var suppTxt = e.support === 'S' ? 'SUPPORT' : 'OPPOSE';
3325 |                         html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3326 |                               + '<div>'
3327 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:rgba(255,255,255,0.8);">' + (e.candidate||'?').substring(0,28) + '</span>'
3328 |                               + '<span style="font-size:7px;color:' + suppCol + ';margin-left:6px;border:1px solid '+suppCol+';padding:1px 4px;border-radius:2px;">' + suppTxt + '</span>'
3329 |                               + '</div>'
3330 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:#f8c15c;">' + amtFmt + '</span>'
3331 |                               + '</div>';
3332 |                     });
3333 |                 }
3334 | 
3335 |                 // Top donations
3336 |                 if (topDons.length) {
3337 |                     html += '<div style="font-size:7px;letter-spacing:.1em;color:rgba(255,255,255,0.25);margin:8px 0 4px;">TOP INDIVIDUAL DONATIONS TO CRYPTO PACs</div>';
3338 |                     topDons.slice(0,4).forEach(function(d2) {
3339 |                         var amtFmt = d2.amount >= 1e6 ? '$'+(d2.amount/1e6).toFixed(1)+'M'
3340 |                                    : d2.amount >= 1e3 ? '$'+(d2.amount/1e3).toFixed(0)+'K'
3341 |                                    : '$'+d2.amount;
3342 |                         var loc = d2.city ? d2.city + ', ' + d2.state : d2.state || '';
3343 |                         html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3344 |                               + '<div>'
3345 |                               + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:rgba(255,255,255,0.8);">' + (d2.donor||'Anonymous').substring(0,26) + '</div>'
3346 |                               + '<div style="font-size:7px;color:rgba(255,255,255,0.3);">' + loc + (d2.employer ? ' · ' + d2.employer.substring(0,20) : '') + '</div>'
3347 |                               + '</div>'
3348 |                               + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:#CC0000;">' + amtFmt + '</span>'
3349 |                               + '</div>';
3350 |                     });
3351 |                 }
3352 | 
3353 |                 if (!exps.length && !topDons.length) {
3354 |                     html += '<div style="color:rgba(255,255,255,0.2);font-size:9px;font-family:\'JetBrains Mono\',monospace;margin-top:8px;">'
3355 |                           + (d.key_type === 'demo' ? 'Add OPENFEC_API_KEY to .env for live data' : 'No recent expenditure data')
3356 |                           + '</div>';
3357 |                 }
3358 | 
3359 |                 html += '<div style="font-size:7px;color:rgba(255,255,255,0.1);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: OpenFEC Public API · FEC.gov</div>';
3360 |                 el.innerHTML = html;
3361 |             })
3362 |             .catch(function(err) {
3363 |                 var el = document.getElementById('pnDonations');
3364 |                 if (el) el.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:9px;font-family:\'JetBrains Mono\',monospace;">Donation data unavailable</div>';
3365 |             });
3366 |     })();
3367 | 
3368 | 
3369 |     {% if not demo_mode %}
3370 |     // ── Make the Bitcoin Case (typewriter 18ms/char, gold cursor) ──
3371 |     window.makeBitcoinCase = function(btn, eventSummary) {
3372 |         var idx = btn.getAttribute('data-idx');
3373 |         var outputEl = document.getElementById('btcCase' + idx);
3374 |         if (!outputEl) return;
3375 | 
3376 |         btn.disabled = true;
3377 |         btn.textContent = 'GENERATING...';
3378 |         outputEl.innerHTML = '';
3379 |         outputEl.classList.add('visible');
3380 | 
3381 |         fetch('/api/panopticon/make-bitcoin-case', {
3382 |             method: 'POST',
3383 |             headers: {'Content-Type': 'application/json'},
3384 |             body: JSON.stringify({event_summary: eventSummary})
3385 |         })
3386 |         .then(function(r) { return r.json(); })
3387 |         .then(function(data) {
3388 |             if (data.error) {
3389 |                 outputEl.innerHTML = '<span style="color:var(--pn-red)">' + data.error + '</span>';
3390 |                 btn.disabled = false;
3391 |                 btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
3392 |                 return;
3393 |             }
3394 |             var text = data.case_text || '';
3395 |             var model = data.model || '';
3396 |             outputEl.innerHTML = '<div class="pn-btc-case-label">THE BITCOIN CASE</div><span id="typewriter' + idx + '"></span><span class="pn-typewriter-cursor"></span>';
3397 |             var twEl = document.getElementById('typewriter' + idx);
3398 |             var i = 0;
3399 |             function typeChar() {
3400 |                 if (i < text.length) {
3401 |                     twEl.textContent += text.charAt(i);
3402 |                     i++;
3403 |                     setTimeout(typeChar, 18 + Math.random() * 12);
3404 |                 } else {
3405 |                     var cursor = outputEl.querySelector('.pn-typewriter-cursor');
3406 |                     if (cursor) cursor.remove();
3407 |                     outputEl.innerHTML += '<div class="pn-btc-case-model">Model: ' + model + '</div>';
3408 |                     btn.disabled = false;
3409 |                     btn.innerHTML = '&#x20BF; Regenerate Case';
3410 |                 }
3411 |             }
3412 |             typeChar();
3413 |         })
3414 |         .catch(function() {
3415 |             outputEl.innerHTML = '<span style="color:var(--pn-red)">Failed to generate. Try again.</span>';
3416 |             btn.disabled = false;
3417 |             btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
3418 |         });
3419 |     };
3420 | 
3421 |     // ── Auto-refresh every 5 minutes ──
3422 |     function refreshData() {
3423 |         fetch('/api/panopticon/whale-alerts')
3424 |             .then(function(r) { return r.json(); })
3425 |             .then(function(data) {
3426 |                 if (data.alerts && data.alerts.length > 0) {
3427 |                     var c = document.getElementById('pnStatWhales');
3428 |                     if (c) c.textContent = data.alerts.length;
3429 |                 }
3430 |             })
3431 |             .catch(function() {});
3432 | 
3433 |         fetch('/api/panopticon/geopolitical')
3434 |             .then(function(r) { return r.json(); })
3435 |             .then(function(data) {
3436 |                 if (data.geopolitical) {
3437 |                     var c = document.getElementById('pnStatGeo');
3438 |                     if (c) c.textContent = data.geopolitical.length;
3439 |                 }
3440 |             })
3441 |             .catch(function() {});
3442 |     }
3443 |     setInterval(refreshData, 300000);
3444 |     {% endif %}
3445 | })();
3446 | 
3447 | 
3448 | /* ═══ CONGRESSIONAL TRADING ═══ */
3449 | (function(){
3450 |   // Recent trades
3451 |   fetch('/api/congress/trades').then(function(r){return r.json()}).then(function(d){
3452 |     var el = document.getElementById('pnCongress');
3453 |     if (!el) return;
3454 |     var trades = d.trades || [];
3455 |     if (!trades.length) { el.innerHTML = '<div style="color:#555;font-size:10px;">No trades available</div>'; return; }
3456 |     var html = '';
3457 |     trades.slice(0, 8).forEach(function(t) {
3458 |       var isBuy = (t.transaction || '').toLowerCase().indexOf('purchase') >= 0;
3459 |       var partyCol = t.party === 'D' ? '#3b82f6' : t.party === 'R' ? '#ef4444' : '#888';
3460 |       html += '<div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-family:\'JetBrains Mono\',monospace;font-size:9px;">';
3461 |       html += '<span style="color:' + partyCol + ';font-weight:700;min-width:14px;">' + (t.party || '?') + '</span>';
3462 |       html += '<span style="color:rgba(255,255,255,0.6);min-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + (t.member || 'Unknown') + '</span>';
3463 |       html += '<span style="color:' + (isBuy ? '#22c55e' : '#ef4444') + ';font-weight:600;min-width:45px;">' + (isBuy ? 'BUY' : 'SELL') + '</span>';
3464 |       html += '<span style="color:#f8c15c;font-weight:700;min-width:40px;">' + (t.ticker || '???') + '</span>';
3465 |       html += '<span style="color:rgba(255,255,255,0.3);margin-left:auto;">' + (t.amount || '') + '</span>';
3466 |       html += '</div>';
3467 |     });
3468 |     if (d.trades && d.trades[0] && d.trades[0].source === 'fallback') {
3469 |       html += '<div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;">Source: Public STOCK Act filings (add QUIVER_API_KEY for live data)</div>';
3470 |     }
3471 |     el.innerHTML = html;
3472 |   }).catch(function(e){ console.warn('Congress trades:', e); });
3473 | 
3474 |   // Party breakdown
3475 |   fetch('/api/congress/trades').then(function(r){return r.json()}).then(function(d){
3476 |     var el = document.getElementById('pnPartyBreakdown');
3477 |     if (!el) return;
3478 |     var pb = d.party_breakdown || {};
3479 |     var html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">';
3480 |     [{k:'D',label:'DEMOCRAT',col:'#3b82f6'},{k:'R',label:'REPUBLICAN',col:'#ef4444'},{k:'I',label:'INDEPENDENT',col:'#888'}].forEach(function(p){
3481 |       var data = pb[p.k] || {buys:0,sells:0,total:0};
3482 |       html += '<div style="text-align:center;padding:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);border-radius:4px;">';
3483 |       html += '<div style="font-size:7px;font-weight:700;letter-spacing:0.12em;color:' + p.col + ';">' + p.label + '</div>';
3484 |       html += '<div style="font-size:18px;font-weight:900;color:#fff;margin-top:4px;">' + data.total + '</div>';
3485 |       html += '<div style="font-size:8px;color:rgba(255,255,255,0.3);margin-top:2px;">' + data.buys + ' BUY / ' + data.sells + ' SELL</div>';
3486 |       html += '</div>';
3487 |     });
3488 |     html += '</div>';
3489 |     el.innerHTML = html;
3490 |   }).catch(function(){});
3491 | 
3492 |   // IHX Score
3493 |   fetch('/api/congress/ihx').then(function(r){return r.json()}).then(function(d){
3494 |     var el = document.getElementById('pnIHX');
3495 |     if (!el) return;
3496 |     var s = d.score || 50;
3497 |     var col = s > 65 ? '#22c55e' : s < 35 ? '#ef4444' : '#f8c15c';
3498 |     var signal = (d.signal || 'neutral').toUpperCase();
3499 |     el.innerHTML = '<div style="display:flex;align-items:center;gap:12px;">'
3500 |       + '<div style="font-size:28px;font-weight:900;color:' + col + ';">' + s + '</div>'
3501 |       + '<div><div style="font-size:10px;font-weight:700;color:' + col + ';">' + signal + '</div>'
3502 |       + '<div style="font-size:8px;color:rgba(255,255,255,0.4);margin-top:2px;">' + (d.interpretation || '') + '</div></div></div>'
3503 |       + '<div style="height:3px;background:rgba(255,255,255,0.04);border-radius:2px;margin-top:8px;"><div style="height:100%;width:' + s + '%;background:' + col + ';border-radius:2px;"></div></div>'
3504 |       + '<div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:6px;">' + (d.trade_count || 0) + ' trades analyzed • ' + (d.crypto_trades || 0) + ' crypto-adjacent</div>';
3505 |   }).catch(function(){});
3506 | 
3507 |   // ── Institutional Accumulation (SEC EDGAR 13F) ─────────────────
3508 |   fetch('/api/panopticon/institutional').then(function(r){return r.json();}).then(function(d){
3509 |     var el13f = document.getElementById('pnInstitutional');
3510 |     var elBanner = document.getElementById('pnCoalitionBanner');
3511 |     var elNote = document.getElementById('pnCoalitionNote');
3512 |     if (!el13f) return;
3513 | 
3514 |     // Coalition banner
3515 |     if (d.coalition_summary && d.coalition_summary.detected && elBanner) {
3516 |       var months = d.coalition_summary.active_months || {};
3517 |       var monthKeys = Object.keys(months);
3518 |       var bestMonth = monthKeys.length ? months[monthKeys[0]] : null;
3519 |       if (bestMonth) {
3520 |         elNote.textContent = bestMonth.note || (bestMonth.filers + ' institutions in coordinated accumulation window');
3521 |         elBanner.style.display = 'block';
3522 |       }
3523 |     }
3524 | 
3525 |     var filers = d.institutional_13f || [];
3526 |     if (!filers.length) { el13f.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;font-family:\'JetBrains Mono\',monospace;">No 13F data in current window</div>'; return; }
3527 | 
3528 |     var html = '<div style="display:flex;flex-direction:column;gap:6px;">';
3529 |     filers.slice(0,8).forEach(function(f){
3530 |       var score = f.coalition_score || 0;
3531 |       var scoreCol = score >= 80 ? '#ef4444' : score >= 50 ? '#f8c15c' : '#888';
3532 |       var tag = f.coalition_detected ? '<span style="background:rgba(204,0,0,0.15);color:#cc0000;font-size:7px;padding:2px 6px;border-radius:3px;letter-spacing:.08em;margin-left:6px;">COALITION</span>' : '';
3533 |       html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3534 |         + '<div><div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:rgba(255,255,255,0.85);">' + f.entity + tag + '</div>'
3535 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.35);margin-top:2px;">' + f.institution_type + ' · ' + (f.filing_date || '') + ' · 13F-HR</div></div>'
3536 |         + '<div style="font-size:9px;color:#22c55e;font-family:\'JetBrains Mono\',monospace;">BTC ETF ↑</div>'
3537 |         + '</div>';
3538 |     });
3539 |     html += '</div><div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: SEC EDGAR 13F · ' + (d.total_institutional_filers || 0) + ' filers</div>';
3540 |     el13f.innerHTML = html;
3541 |   }).catch(function(){ });
3542 | 
3543 |   // ── Private Equity Datastream (Form D + Coalition) ────────────
3544 |   fetch('/api/panopticon/pe-datastream').then(function(r){return r.json();}).then(function(d){
3545 |     var elPE = document.getElementById('pnPEDatastream');
3546 |     if (!elPE) return;
3547 |     var rounds = d.pe_rounds || [];
3548 |     if (!rounds.length) { elPE.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;font-family:\'JetBrains Mono\',monospace;">No PE rounds in current window</div>'; return; }
3549 | 
3550 |     var html = '';
3551 |     if (d.coalition_active) {
3552 |       html += '<div style="background:rgba(204,0,0,0.08);border-left:3px solid #cc0000;padding:8px 12px;margin-bottom:10px;border-radius:0 4px 4px 0;">'
3553 |         + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:8px;letter-spacing:.15em;color:#cc0000;font-weight:700;">COALITION EFFECT ACTIVE</div>'
3554 |         + '<div style="font-size:10px;color:rgba(255,255,255,0.6);margin-top:4px;">' + (d.insight || '') + '</div>'
3555 |         + '</div>';
3556 |     }
3557 | 
3558 |     html += '<div style="display:flex;flex-direction:column;gap:6px;">';
3559 |     rounds.slice(0,8).forEach(function(r){
3560 |       html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
3561 |         + '<div><div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:rgba(255,255,255,0.85);">' + r.entity + '</div>'
3562 |         + '<div style="font-size:8px;color:rgba(255,255,255,0.35);margin-top:2px;">' + (r.filing_date || '') + ' · Form D · Digital Assets</div></div>'
3563 |         + '<div style="font-size:9px;color:#f8c15c;font-family:\'JetBrains Mono\',monospace;">RAISE ↑</div>'
3564 |         + '</div>';
3565 |     });
3566 |     html += '</div><div style="font-size:7px;color:rgba(255,255,255,0.2);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">Source: SEC EDGAR Form D · ' + (d.pe_count || 0) + ' rounds</div>';
3567 |     elPE.innerHTML = html;
3568 |   }).catch(function(){ });
3569 | 
3570 | 
3571 |   // ── Bitcoin Bill Gap Tracker ──────────────────────────────────────────────
3572 |   (function loadBillTracker() {
3573 |     var el = document.getElementById('pnBillTracker');
3574 |     if (!el) return;
3575 | 
3576 |     fetch('/api/panopticon/bills')
3577 |       .then(function(r) { return r.json(); })
3578 |       .then(function(data) {
3579 |         var bills = (data.bills || []).slice(0, 12);
3580 |         if (!bills.length) {
3581 |           el.innerHTML = '<div style="color:rgba(255,255,255,0.2);font-size:10px;">No active Bitcoin legislation found</div>';
3582 |           return;
3583 |         }
3584 | 
3585 |         var html = '<div style="display:flex;flex-direction:column;gap:10px;">';
3586 | 
3587 |         bills.forEach(function(b) {
3588 |           var gap = b.gap_score !== null ? b.gap_score : null;
3589 |           var gapCol = gap === null ? '#888' : gap >= 40 ? '#ef4444' : gap >= 20 ? '#f97316' : '#22c55e';
3590 |           var gapLabel = b.gap_label || 'PENDING';
3591 |           var congPct = b.congress_pct || 0;
3592 |           var pubPct  = b.public_pct  || 50;
3593 |           var hasCongVote = b.vote_tally && b.vote_tally.total > 0;
3594 |           var btcCol = b.btc_signal === 'bullish' ? '#22c55e' : b.btc_signal === 'bearish' ? '#ef4444' : '#888';
3595 |           var cats = (b.categories || []).join(', ').replace(/_/g,' ');
3596 | 
3597 |           html += '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:10px 12px;">';
3598 | 
3599 |           // Header row
3600 |           html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
3601 |             + '<div>'
3602 |             + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;color:rgba(255,255,255,0.9);">'
3603 |             + b.bill_number + ' — ' + (b.short_title || '').substring(0,40) + '</div>'
3604 |             + '<div style="font-size:7px;color:rgba(255,255,255,0.3);margin-top:2px;text-transform:uppercase;letter-spacing:.06em;">'
3605 |             + cats.substring(0,35) + '</div>'
3606 |             + '</div>'
3607 |             + '<div style="text-align:right;flex-shrink:0;margin-left:8px;">'
3608 |             + (gap !== null ? '<div style="font-family:\'JetBrains Mono\',monospace;font-size:14px;font-weight:900;color:' + gapCol + ';">' + gap + '%</div>'
3609 |                            : '<div style="font-size:8px;color:#888;font-family:\'JetBrains Mono\',monospace;">PENDING</div>')
3610 |             + '<div style="font-size:6px;letter-spacing:.1em;color:' + gapCol + ';font-weight:700;">GAP</div>'
3611 |             + '</div>'
3612 |             + '</div>';
3613 | 
3614 |           // Progress bars
3615 |           html += '<div style="display:flex;flex-direction:column;gap:5px;margin-bottom:6px;">';
3616 | 
3617 |           // Public bar
3618 |           html += '<div style="display:flex;align-items:center;gap:6px;">'
3619 |             + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;flex-shrink:0;font-family:\'JetBrains Mono\',monospace;">PUBLIC</div>'
3620 |             + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;position:relative;">'
3621 |             + '<div style="height:100%;width:' + pubPct + '%;background:linear-gradient(90deg,#22c55e,#16a34a);border-radius:3px;transition:width .8s ease;"></div>'
3622 |             + '</div>'
3623 |             + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;font-weight:700;color:#22c55e;width:30px;text-align:right;">' + pubPct + '%</div>'
3624 |             + '</div>';
3625 | 
3626 |           // Congress bar
3627 |           if (hasCongVote) {
3628 |             var congBarColor = congPct >= 67 ? '#22c55e' : congPct >= 50 ? '#f8c15c' : '#ef4444';
3629 |             var nayPct = 100 - congPct;
3630 |             html += '<div style="display:flex;align-items:center;gap:6px;">'
3631 |               + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;flex-shrink:0;font-family:\'JetBrains Mono\',monospace;">CONGRESS</div>'
3632 |               + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;display:flex;">'
3633 |               + '<div style="height:100%;width:' + congPct + '%;background:' + congBarColor + ';transition:width .8s ease;"></div>'
3634 |               + '<div style="height:100%;width:' + nayPct + '%;background:#ef4444;opacity:0.5;"></div>'
3635 |               + '</div>'
3636 |               + '<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;font-weight:700;color:' + congBarColor + ';width:30px;text-align:right;">' + congPct + '%</div>'
3637 |               + '</div>';
3638 |           } else {
3639 |             html += '<div style="display:flex;align-items:center;gap:6px;">'
3640 |               + '<div style="font-size:7px;color:rgba(255,255,255,0.4);width:50px;font-family:\'JetBrains Mono\',monospace;">CONGRESS</div>'
3641 |               + '<div style="flex:1;height:14px;background:rgba(255,255,255,0.04);border-radius:3px;display:flex;align-items:center;padding-left:8px;">'
3642 |               + '<span style="font-size:7px;color:rgba(255,255,255,0.2);font-family:\'JetBrains Mono\',monospace;">NO VOTE YET</span>'
3643 |               + '</div></div>';
3644 |           }
3645 | 
3646 |           html += '</div>'; // end bars
3647 | 
3648 |           // Footer: status + vote buttons
3649 |           html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">'
3650 |             + '<div>'
3651 |             + '<span style="font-size:7px;color:rgba(255,255,255,0.3);">' + (b.status||'') + '</span>'
3652 |             + (b.sponsor ? '<span style="font-size:7px;color:rgba(255,255,255,0.2);margin-left:8px;">Sponsor: ' + b.sponsor.substring(0,20) + '</span>' : '')
3653 |             + '</div>'
3654 |             + '<div style="display:flex;gap:4px;align-items:center;">'
3655 |             + '<span style="font-size:7px;color:rgba(255,255,255,0.25);font-family:\'JetBrains Mono\',monospace;">SHOULD PASS?</span>'
3656 |             + '<button onclick="castBillVote(' + b.bill_id + ',\'' + b.bill_number + '\',\'yes\')" '
3657 |             +   'style="background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);color:#22c55e;padding:2px 8px;border-radius:3px;font-size:8px;font-family:\'JetBrains Mono\',monospace;cursor:pointer;letter-spacing:.08em;">YES</button>'
3658 |             + '<button onclick="castBillVote(' + b.bill_id + ',\'' + b.bill_number + '\',\'no\')" '
3659 |             +   'style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;padding:2px 8px;border-radius:3px;font-size:8px;font-family:\'JetBrains Mono\',monospace;cursor:pointer;letter-spacing:.08em;">NO</button>'
3660 |             + '</div>'
3661 |             + '</div>';
3662 | 
3663 |           html += '</div>'; // end card
3664 |         });
3665 | 
3666 |         html += '</div>';
3667 |         html += '<div style="font-size:7px;color:rgba(255,255,255,0.15);margin-top:8px;font-family:\'JetBrains Mono\',monospace;">'
3668 |           + 'Source: LegiScan API (CC BY 4.0) · ' + data.total_bills + ' bills tracked'
3669 |           + '</div>';
3670 |         el.innerHTML = html;
3671 |       })
3672 |       .catch(function(e) {
3673 |         if (el) el.innerHTML = '<div style="color:rgba(255,255,255,0.15);font-size:9px;">Bill tracker unavailable</div>';
3674 |       });
3675 |   })();
3676 | 
3677 |   function castBillVote(billId, billNumber, vote) {
3678 |     fetch('/api/panopticon/bills/vote', {
3679 |       method: 'POST',
3680 |       headers: {'Content-Type': 'application/json'},
3681 |       body: JSON.stringify({bill_id: billId, bill_number: billNumber, vote: vote})
3682 |     })
3683 |     .then(function(r) { return r.json(); })
3684 |     .then(function(d) {
3685 |       if (d.success) {
3686 |         // Flash the bill card
3687 |         var cards = document.querySelectorAll('#pnBillTracker > div > div');
3688 |         // Reload the tracker to show updated votes
3689 |         setTimeout(function() {
3690 |           document.getElementById('pnBillTracker').innerHTML =
3691 |             '<div style="color:rgba(34,197,94,0.8);font-size:9px;font-family:\'JetBrains Mono\',monospace;padding:8px;">Vote recorded. Reloading...</div>';
3692 |           setTimeout(function() { loadBillTracker(); }, 1500);
3693 |         }, 300);
3694 |       }
3695 |     })
3696 |     .catch(function() {});
3697 |   }
3698 | 
3699 | })();
3700 | 
3701 | </script>
3702 | {% endblock %}
3703 | 
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
