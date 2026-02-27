# World-Class Upgrade Priorities — Protocol Pulse

**Purpose:** Where to invest next so the site feels premium, converts, and retains. Ordered by impact and effort.

---

## 1. **404 & 500 pages** — Fast win, big impression

**Current:** Literally `<h1>404 Not Found</h1>` and `<h1>500 Error</h1>` with no layout or branding.

**Why it matters:** Every broken link or server hiccup lands here. A generic error page undercuts the “intelligence briefing” brand and wastes the moment.

**World-class upgrade:**
- Full-page layout using `base.html` (nav + footer) and Protocol Pulse tokens (dark bg, accent red, JetBrains Mono).
- **404:** Short copy (“Intel not found”), search or “Back to base”, and clear CTAs: **The Dossier**, **Latest Intel**, **Live Terminal**, **Donate**.
- **500:** “We’re restoring the signal” + status link (e.g. status page or Twitter) + “Try again” / “Go home”.
- Optional: 404 could suggest the closest article by slug (e.g. fuzzy match on URL path).

**Effort:** Low (1–2 templates + one error handler tweak).

---

## 2. **Donate Bitcoin / value-for-value flow** — Core to mission

**Current:** Donate Bitcoin page has Lightning + on-chain; donate (fiat) page is solid. Flow after giving is weak.

**Why it matters:** Value-for-value is a differentiator. Making it obvious, easy, and rewarding (including post-donate) increases one-time and repeat support.

**World-class upgrade:**
- **Donate Bitcoin page:** One clear “Recommended: Lightning” path (amount presets + QR + copy invoice), then “Or use on-chain” collapsed/secondary. One sentence: “This keeps us ad-free and sovereign.”
- **Post-donate (thanks page):** Same treatment as Dossier finale: “You’re supporting the signal. Next: run through **The Dossier** or share a brief.” Link to `/dossier` and `/articles`. Optional: “Get a receipt by email” (collect email, send later or via existing GHL).
- **Donate (fiat) thanks:** Same idea — “What to do next” (Dossier, Premium Hub, follow on X/Nostr).

**Effort:** Medium (copy + layout + optional email capture).

---

## 3. **Homepage “path to value”** — First 10 seconds

**Current:** Strong hero, live stats, whale strip, command center grid, briefs. Missing: one obvious “start here” for new visitors and a clear path to Dossier / Premium / Donate.

**Why it matters:** New visitors need one clear next step; power users need fast paths to Terminal, Dossier, Hub.

**World-class upgrade:**
- **Above the fold:** Add a single line under the hero CTAs: e.g. “New? Start with **[The Dossier]( /dossier)** — 32 intel briefs on why Bitcoin wins.” Or a small “New here?” pill that scrolls to a 3-step (Dossier → Live tools → Support).
- **Command Center section:** Ensure **The Dossier** and **Premium Hub** (or “Command Center”) are visible in the grid with the same treatment as Live Terminal / Whale Watcher.
- **Footer or sticky:** One “Support the signal” that goes to `/donate/bitcoin` (not buried in nav).

**Effort:** Low–medium (copy + 1–2 links + optional “New here?” block).

---

## 4. **Article detail page** — Engagement and shares

**Current:** Good structure: breadcrumb, category, title, meta, hero image, content, OG/Twitter meta. Missing: stronger “next step” and support.

**World-class upgrade:**
- **After content:** “Next read” (one related article by category or recency) + “More in **[Latest Intel](/articles)**”.
- **Sticky or inline:** “Support this brief” → tip jar (sats/dollars) and “Share” (X, Nostr, copy link) with prefill copy.
- **TL;DR:** If `article.summary` or a TL;DR block exists, show it at the top in a collapsed “TL;DR” strip (consistent with your existing `clean_preview`/TL;DR usage).
- **Pro badge:** If `article.premium_tier` is set, show a small “Commander brief” or “Pro” badge so premium feels real.

**Effort:** Medium (related-article query + template block + share/tip UI).

---

## 5. **Login & signup** — Trust and clarity

**Current:** Centered card, username/password, “Forgot Password?” (link to `#`). Looks generic.

**Why it matters:** First touch for Hub, drills, and preferences. Should feel like part of Protocol Pulse, not a default Bootstrap form.

**World-class upgrade:**
- **Visual:** Use same background and tokens as Premium/Dossier (dark, red accent, JetBrains Mono for labels). Same card style as `premium.html` / `donate.html`.
- **Copy:** One line: “Sign in to access the Hub, drills, and your intel preferences.”
- **Forgot password:** Either implement a simple “email me a reset link” flow or replace with “Contact us to recover access” linking to `/contact`.
- **Signup:** Same treatment; short “Why sign up” (Hub, Dossier progress, alerts).

**Effort:** Medium (styling + copy; forgot-password is extra if implemented).

---

## 6. **Subscription success** — First action after paying

**Current:** User lands on success page after Stripe checkout; may not know what to do next.

**World-class upgrade:**
- **Headline:** “You’re in. Here’s your command center.”
- **One primary CTA:** “Open Premium Hub” (or “Open Hub”) → `/hub`.
- **Secondary:** “Run through **The Dossier**” → `/dossier`, “Latest Intel” → `/articles`.
- Optional: Short “What you get” (whale feed, Pro Briefs, etc.) so the value is reinforced.

**Effort:** Low (one template + copy).

---

## 7. **Articles listing** — Scan and filter

**Current:** Already has a strong “news pulse” look (grid, scanline, zones). Could make discovery and “Pro” clearer.

**World-class upgrade:**
- **Filters:** By category (Bitcoin, DeFi, etc.) and optionally “Pro only” for Commander+ (or “Featured”).
- **Cards:** Show “Pro” or “Featured” badge when `article.premium_tier` or `article.featured` is set; estimate read time if not already present.
- **Above the list:** One line: “New to sovereignty? Start with **[The Dossier](/dossier)**.”

**Effort:** Low–medium (query params + badges + one CTA).

---

## 8. **Contact page** — Reliability and tone

**Current:** Clean form and layout. Could align with rest of site and set expectations.

**World-class upgrade:**
- Use same design tokens and card style as other “utility” pages (donate, contact already close).
- Short line: “We read everything. For access recovery or partnership, mention it in the message.”
- After submit: “Signal received. We’ll respond within 24–48 hours.” + link to Home or Dossier.

**Effort:** Low (copy + optional success message).

---

## 9. **Live Terminal / Media Hub** — Depth without overwhelm

**Current:** Feature-rich; new users may not know where to look.

**World-class upgrade:**
- **Live Terminal:** Optional “Quick tour” (tooltip or 3-step overlay): “This is the mempool → these are whales → this is difficulty.” Dismissible, stored in localStorage.
- **Media Hub:** “Start here” or “New to the show?” pointing to one flagship series or episode (e.g. Sovereignty 101 or first episode).

**Effort:** Medium (JS overlay + copy).

---

## 10. **Merchant map** — Completeness and growth

**Current:** Solid Leaflet map and sidebar. Could encourage contribution and filtering.

**World-class upgrade:**
- “Add a merchant” or “Suggest a location” CTA (links to contact with prefill “Merchant suggestion” or a simple form).
- Filters (e.g. by category or “Lightning only”) if the data model supports it.

**Effort:** Low–medium (CTA + optional filters).

---

## Summary order (by impact / effort)

| Priority | Area              | Impact        | Effort   |
|----------|-------------------|---------------|----------|
| 1        | 404 & 500         | High (brand)  | Low      |
| 2        | Donate Bitcoin    | High (revenue)| Medium   |
| 3        | Homepage path     | High (conversion) | Low–Med |
| 4        | Article detail    | Medium (engagement) | Medium |
| 5        | Login / signup    | Medium (trust)| Medium   |
| 6        | Subscription success | Medium (retention) | Low |
| 7        | Articles listing  | Medium        | Low–Med  |
| 8        | Contact           | Lower         | Low      |
| 9        | Live / Media tour | Lower         | Medium   |
| 10       | Merchant map      | Lower         | Low–Med  |

**Suggested first sprint:** 404/500 (1) + Subscription success (6) + Homepage path (3). Then Donate Bitcoin flow (2) and Article detail (4).
