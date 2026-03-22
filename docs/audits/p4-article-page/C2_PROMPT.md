# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: p4-article-page
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

There is no implementation here for `p4-article-page` to audit — only:
- `.gitignore`
- `ARTICLE_PAGE_LAWS.md`

So the feature does **not** currently do what it claims. There are no API routes, no model changes, no migration, no frontend, no redirects, no tests, and no evidence of any article-page code being added.

### Main user flow walkthrough
Expected flow per spec:
1. User visits `/articles`
2. Backend serves paginated article JSON from `/api/v2/articles`
3. Frontend renders listing with category filters and pagination
4. User clicks article
5. Frontend fetches `/api/v2/articles/{slug}`
6. Detail page SSR renders article with SEO metadata

### Actual state in this package
- Step 1: No Next.js frontend exists in provided files.
- Step 2: No `/api/v2/articles` implementation exists.
- Step 3: No category endpoint exists.
- Step 4: No slug route implementation exists.
- Step 5: No migration script exists.
- Step 6: No redirect/deprecation logic exists.

### Concrete correctness findings
1. **Feature is effectively unimplemented**
   - Evidence: only `.gitignore` and `ARTICLE_PAGE_LAWS.md` are present.
   - Impact: merge would add documentation, not functionality.

2. **Internal spec inconsistency: pagination design conflicts**
   - Law 2 defines query params `page` and `per_page` and response with `total_pages`/`has_next`/`has_prev` (`ARTICLE_PAGE_LAWS.md:150-157`, `136-143`), which is classic page-number pagination.
   - Law 6 says “Pagination is cursor-based in the API but rendered as page numbers in the UI” (`ARTICLE_PAGE_LAWS.md:172-175`).
   - These are contradictory. A page/per_page schema is not cursor-based.
   - Impact: implementers can build incompatible APIs.

3. **Internal spec inconsistency: fallback image algorithm conflicts**
   - Law 1 fallback: `/static/images/default-covers/btc-{article_id % 10}.jpg` (`ARTICLE_PAGE_LAWS.md:108-110`)
   - Factory example fallback: `btc-{hash(slug) % 10}.jpg` (`ARTICLE_PAGE_LAWS.md:389-390`)
   - Impact: inconsistent image assignment across creation paths.

4. **Internal spec inconsistency: database backend conflicts with stated stack**
   - Technology stack says SQLite via SQLAlchemy ORM.
   - Laws doc architecture says PostgreSQL stays unchanged and search uses PostgreSQL ILIKE (`ARTICLE_PAGE_LAWS.md:67-72`, `89-92`, `257`).
   - Impact: implementation guidance is contradictory; SQLite does not support PostgreSQL-specific behavior/indexing strategy.

5. **Potential repo hygiene issue in `.gitignore`**
   - Ignoring `*.png` and `*.jpg` globally (`.gitignore:15-16`) would block committing required deterministic fallback cover images mandated by Law 1 (`ARTICLE_PAGE_LAWS.md:109`).
   - Impact: required assets may never be versioned.

Because no executable code is present, there are no race conditions, N+1s, or runtime logic bugs to inspect directly. The dominant correctness issue is **absence of implementation** plus **spec contradictions that will cause incorrect implementation later**.

---

## SECTION 2: LAW COMPLIANCE

Since there is no feature implementation, almost every law is a **VIOLATION** by absence.

### Law 1: One Source of Truth for Article Images
**VIOLATION**
- No code exists enforcing `cover_image_url`.
- No evidence of deprecating `header_image_url`.
- No fallback image assets or logic.
- Spec conflict on fallback path algorithm (`ARTICLE_PAGE_LAWS.md:109` vs `389-390`).

### Law 2: One API, One Schema
**VIOLATION**
- No `/api/v2/articles` endpoint exists in provided code.
- No schema implementation exists.
- Contradiction in pagination model (`ARTICLE_PAGE_LAWS.md:150-157` vs `172-175`).

### Law 3: No Jinja in the Critical Path
**PARTIAL**
- No new Jinja code was added.
- But no redirect logic exists to move visitor-facing pages to Next.js (`ARTICLE_PAGE_LAWS.md:160-163`).
- Since no frontend exists, the law is not satisfied operationally.

### Law 4: Every Article Has a Slug
**VIOLATION**
- No `slug` column implementation.
- No migration script.
- No unique/indexed slug evidence.
- Required in `ARTICLE_PAGE_LAWS.md:164-167`, `221`.

### Law 5: Server-Side Rendering for Article Pages
**VIOLATION**
- No Next.js app or SSR page exists.
- Required by `ARTICLE_PAGE_LAWS.md:168-170`.

### Law 6: Pagination is Mandatory
**VIOLATION**
- No listing endpoint or frontend pagination exists.
- Also spec contradiction on cursor vs page-number API (`ARTICLE_PAGE_LAWS.md:174`).

### Law 7: Category Filters Work or Don't Exist
**VIOLATION**
- No `/api/v2/categories` endpoint.
- No frontend filter implementation.
- Required by `ARTICLE_PAGE_LAWS.md:176-179`.

### Law 8: Mobile-First, Dark-Mode-First
**VIOLATION**
- No frontend implementation exists.

### Law 9: Performance Budget
**VIOLATION**
- No implementation to measure.
- No image optimization, no page-size controls, no ISR/SSR code.

### Law 10: Content Generator Contract
**VIOLATION**
- No enforcement in model `__init__`, hook, or factory.
- No evidence any creation path

## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REPORT: p4-article-page

As one of the AI models reviewing this code for Protocol Pulse, I will provide a thorough and honest assessment based on the provided documentation and specifications. Since no actual code files beyond `.gitignore` and the specification document `ARTICLE_PAGE_LAWS.md` are provided for review, my analysis will focus on the structure, planning, and potential issues within the migration plan and laws outlined in the documentation. I will treat the `ARTICLE_PAGE_LAWS.md` as the blueprint for the intended implementation and evaluate its completeness, feasibility, and compliance with best practices.

---

### SECTION 1: CORRECTNESS
Since no executable code is provided (e.g., Flask API routes, Next.js components), I cannot directly assess logic errors, race conditions, or N+1 query problems. However, I will evaluate the correctness of the migration plan and architecture as described in `ARTICLE_PAGE_LAWS.md`.

- **Main User Flow (Based on Spec):** The user flow involves visitors accessing `protocolpulse.io`, which serves a Next.js frontend that fetches data from a Flask API backend. Article listing pages use Incremental Static Regeneration (ISR), while individual article pages use Server-Side Rendering (SSR). The flow includes pagination, category filtering, and search functionality.
  - **Potential Logic Errors in Plan:** The spec mandates ISR for listing pages with a 60-second revalidation (Line 170). This could lead to stale data for users if significant updates occur within that window, especially for a Bitcoin intelligence platform where real-time data (e.g., BTC ticker) is critical. No mechanism is described to force immediate revalidation on critical updates.
  - **Race Conditions:** The plan does not address potential race conditions in the Flask API during high-concurrency scenarios (~1000 concurrent users at peak, as per tech stack). For instance, if multiple requests hit pagination endpoints simultaneously, there’s no mention of caching or rate-limiting strategies to prevent DB overload.
  - **Edge Cases:** The spec does not account for scenarios like API timeouts or failures in the Next.js frontend (e.g., what happens if `/api/v2/articles` is down?). There’s no mention of fallback UI states or offline handling in the frontend design (Lines 268-301).
  - **N+1 Query Problem:** While not evident in code, the spec’s API design (Line 158) suggests that fetching individual articles includes the full `content` field. If related data (e.g., tags, categories) is fetched separately or in loops, this could introduce N+1 issues unless explicitly optimized in the `to_api_dict()` method (Line 220).

**Conclusion:** The plan is conceptually sound but lacks detail on handling edge cases and concurrency, which could lead to production issues if not addressed in implementation.

---

### SECTION 2: LAW COMPLIANCE
Evaluating compliance with the 10 laws outlined in `ARTICLE_PAGE_LAWS.md` (Lines 104-210). Since no code is provided, I assess the spec’s adherence to its own laws and potential gaps in enforcement.

- **Law 1: One Source of Truth for Article Images (Lines 104-110)** - **COMPLIANT** - The spec clearly mandates `cover_image_url` as the sole image field and deprecates `header_image_url`. It includes a fallback mechanism for missing images (Line 109).
- **Law 2: One API, One Schema (Lines 112-159)** - **COMPLIANT** - The API schema is well-defined with pagination and query parameters. The distinction between listing (no `content`) and detail (with `content`) responses is clear (Line 158).
- **Law 3: No Jinja in the Critical Path (Lines 161-163)** - **COMPLIANT** - The spec mandates Next.js for visitor-facing pages and restricts Jinja to admin use, with redirects for old routes (Line 163).
- **Law 4: Every Article Has a Slug (Lines 165-167)** - **COMPLIANT** - Slugs are required, stored in DB, and indexed. A migration script for existing articles is planned (Line 167).
- **Law 5: Server-Side Rendering for Article Pages (Lines 169-171)** - **COMPLIANT** - SSR for individual pages and ISR for listings are explicitly required, ensuring SEO and freshness (Line 170).
- **Law 6: Pagination is Mandatory (Lines 173-176)** - **COMPLIANT** - Pagination is enforced with a max of 50 articles per request, and UI options (page numbers or infinite scroll) are specified (Line 175).
- **Law 7: Category Filters Work or Don’t Exist (Lines 178-181)** - **COMPLIANT** - Filters must be functional or not rendered at all, avoiding dead UI elements (Line 181).
- **Law 8: Mobile-First, Dark-Mode-First (Lines 183-188)** - **COMPLIANT** - Design prioritizes dark mode and mobile-first layouts with specific breakpoints and typography rules (Lines 186-187).
- **Law 9: Performance Budget (Lines 190-196)** - **COMPLIANT** - Strict performance targets are set (e.g., LCP < 2.5s), with image optimization via Next.js `<Image>` (Line 195).
- **Law 10: Content Generator Contract (Lines 198-209)** - **COMPLIANT** 

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — P4-ARTICLE-PAGE — CYCLE 1
Generated: 2026-03-09 18:52
Models: gpt4o, grok (+1 failed — Gemini 2.5 Pro: 403 PERMISSION_DENIED / leaked API key)

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok | Consensus |
|------------------|--------|--------|------|-----------|
| Correctness      | N/A    | 0/10   | 2/10 | **1/10**  |
| Law Compliance   | N/A    | 0/10   | 7/10 | **3/10**  |
| Security         | N/A    | 1/10   | 2/10 | **1/10**  |
| Frontend Quality | N/A    | 0/10   | 0/10 | **0/10**  |
| Backend Quality  | N/A    | 0/10   | 0/10 | **0/10**  |
| Overall          | N/A    | 0/10   | 2/10 | **1/10**  |

> **Scoring note:** GPT-4o scored the feature at or near zero across all dimensions because no implementation exists. Grok rated the *spec document itself* and gave it credit for internal coherence, producing inflated scores. The consensus weights GPT-4o's harder interpretation more heavily because the audit object is a deliverable feature, not a planning document. A spec without code is a 1/10 feature, not a 7/10 feature.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

---

### U1 — The feature is entirely unimplemented
**What it is:** The submitted package contains only `.gitignore` and `ARTICLE_PAGE_LAWS.md`. No API routes, no database migration, no model changes, no Next.js pages, no tests, no static assets exist anywhere in the deliverable.

**Files affected:** Entire feature directory (empty except two files)

**What to change:** Build the feature. Every artifact listed in the action plan below must be created from scratch. This is not a polish pass — it is a first build.

---

### U2 — `.gitignore` blocks required static assets
**What it is:** `.gitignore` contains global rules for `*.png` and `*.jpg`. The spec mandates deterministic fallback cover images at `/static/images/default-covers/btc-{n}.jpg` (Law 1, `ARTICLE_PAGE_LAWS.md:109`). These files can never be committed under the current ignore rules.

**File:** `.gitignore:15-16`

**What to change:**
```gitignore
# Replace blanket image ignores with scoped ignores
# BAD (current):
*.png
*.jpg

# GOOD (replacement):
# Ignore user-uploaded images in media directories only
media/uploads/*.png
media/uploads/*.jpg
# Never ignore versioned static assets
```

---

### U3 — No rate limiting defined or implemented for public endpoints
**What it is:** Both models independently flagged that the spec defines public unauthenticated read endpoints (`ARTICLE_PAGE_LAWS.md:223-235`) at a projected peak of ~1000 concurrent users, with zero throttling strategy described or implemented anywhere.

**Files affected:** No implementation exists yet; must be included in initial build.

**What to change:** Add Flask-Limiter decorators to all `/api/v2/articles*` endpoints. Minimum: `100/minute` per IP on listing, `200/minute` per IP on detail. Document limits in the spec.

---

### U4 — No input validation on query parameters
**What it is:** Both mo

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: .gitignore (17 lines)
```
   1 | *.mp4
   2 | *.wav
   3 | *.pyc
   4 | __pycache__/
   5 | logs/
   6 | night_prompts/
   7 | *.log
   8 | instance/
   9 | test_*
  10 | /tmp/
  11 | .env
  12 | venv/
  13 | data/episodes/
  14 | *.mp3
  15 | *.png
  16 | *.jpg
  17 | 
```

### File: ARTICLE_PAGE_LAWS.md (507 lines)
```
   1 | # ARTICLE PAGE LAWS v1.0
   2 | 
   3 | ## Protocol Pulse — Article Frontend Migration Spec
   4 | 
   5 | **Status:** GOSPEL. Load this into EVERY Claude Code session touching article code.
   6 | **Created:** 2026-03-04
   7 | **Authority:** PBX + Claude Opus forensic audit
   8 | 
   9 | ---
  10 | 
  11 | ## PART 1: THE DAMAGE REPORT (Forensic Audit Findings)
  12 | 
  13 | ### What We Found
  14 | 
  15 | | Problem | Evidence |
  16 | |---------|----------|
  17 | | Jinja template sprawl | 2,539 lines across 3 files: articles.html, article_detail.html, article_master.html |
  18 | | Monolith route file | 8,472 lines in routes.py — one file handling everything |
  19 | | Article creation chaos | 16 different Article() creation paths across 6 files |
  20 | | Cover image failures | cover_image_url not set by content generator; 183 articles published without images before manual backfill |
  21 | | Useless API | Only public JSON endpoint is /api/latest-articles — returns 6 articles with 4 fields |
  22 | | No pagination | 1,704 articles, only 40 displayed. No load-more, no page numbers, no infinite scroll |
  23 | | Dead category filters | 19 categories in DB, filter UI exists but non-functional |
  24 | | Column sprawl | 24 database columns on Article model, many unused or redundant |
  25 | | Dual image columns | Both header_image_url (local PIL files) and cover_image_url (Pexels URLs) — generator writes to one, template reads the other |
  26 | 
  27 | ### Root Cause
  28 | 
  29 | The Flask/Jinja frontend was built incrementally by AI agents over months. Each agent added features without understanding the full system. Result: 16 creation paths where each one handles images differently, a route file no human or AI can reason about, and templates that paper over backend inconsistencies with 5 layers of fallback logic.
  30 | 
  31 | **Verdict: The Jinja frontend is unreformable. We replace it.**
  32 | 
  33 | ---
  34 | 
  35 | ## PART 2: THE ARCHITECTURE
  36 | 
  37 | ### Target Stack (Zero Additional Cost)
  38 | 
  39 | ```
  40 | ┌─────────────────────────────────────────────────┐
  41 | │                    VISITORS                       │
  42 | │              protocolpulse.io                     │
  43 | └────────────────────┬────────────────────────────┘
  44 |                      │
  45 |           ┌──────────▼──────────┐
  46 |           │    Next.js Frontend   │
  47 |           │   (Vercel, free tier) │
  48 |           │                       │
  49 |           │  React components     │
  50 |           │  Server-side render   │
  51 |           │  Static generation    │
  52 |           │  Image optimization   │
  53 |           │  Built-in pagination  │
  54 |           └──────────┬───────────┘
  55 |                      │ JSON API calls
  56 |           ┌──────────▼──────────┐
  57 |           │    Flask API Layer    │
  58 |           │  (Replit, existing)   │
  59 |           │                       │
  60 |           │  /api/v2/articles     │
  61 |           │  /api/v2/categories   │
  62 |           │  /api/v2/search       │
  63 |           │  /api/v2/prices       │
  64 |           └──────────┬───────────┘
  65 |                      │
  66 |           ┌──────────▼──────────┐
  67 |           │     PostgreSQL        │
  68 |           │  (Replit, existing)   │
  69 |           │                       │
  70 |           │  1,704 articles       │
  71 |           │  All cover images     │
  72 |           │  Categories, tags     │
  73 |           └──────────────────────┘
  74 | 
  75 |           ┌──────────────────────┐
  76 |           │   Ultron (unchanged)  │
  77 |           │                       │
  78 |           │  Video pipeline       │
  79 |           │  Avatar system        │
  80 |           │  Claude Code sessions │
  81 |           │  Git push origin      │
  82 |           └──────────────────────┘
  83 | ```
  84 | 
  85 | ### What Changes vs. What Stays
  86 | 
  87 | | Component | Action |
  88 | |-----------|--------|
  89 | | PostgreSQL database | STAYS. Zero changes. |
  90 | | Article content generator | STAYS. Only change: guaranteed cover_image_url on every new article (already patched). |
  91 | | Flask app on Replit | STAYS as API-only backend. Jinja templates get deprecated, not deleted (keep for admin). |
  92 | | routes.py article routes | REPLACED by 3 clean API endpoints. Old Jinja routes marked @deprecated. |
  93 | | Jinja templates (articles.html etc.) | RETIRED. Replaced by Next.js React pages. |
  94 | | Ultron pipeline | UNCHANGED. Zero touches. |
  95 | | Cloudflare DNS | UPDATE: protocolpulse.io points to Vercel. API subdomain api.protocolpulse.io points to Replit. |
  96 | | Video pipeline, tweet system, Oracle Briefings | UNCHANGED. |
  97 | 
  98 | ---
  99 | 
 100 | ## PART 3: THE LAWS
 101 | 
 102 | These are permanent. Every session must obey them.
 103 | 
 104 | ### Law 1: One Source of Truth for Article Images
 105 | 
 106 | The column is `cover_image_url`. Period. It contains a full HTTPS Pexels URL.
 107 | - `header_image_url` is DEPRECATED. Never read it, never write it in new code.
 108 | - Every Article() creation path MUST set cover_image_url before commit.
 109 | - If Pexels fails, set cover_image_url to a deterministic fallback: `/static/images/default-covers/btc-{article_id % 10}.jpg` (10 pre-generated default images).
 110 | - The API never returns header_image_url. Only cover_image_url.
 111 | 
 112 | ### Law 2: One API, One Schema
 113 | 
 114 | All article data flows through `/api/v2/articles`. The response schema is:
 115 | 
 116 | ```json
 117 | {
 118 |   "articles": [
 119 |     {
 120 |       "id": 1874,
 121 |       "title": "Bitcoin Network Implements Taproot Upgrade",
 122 |       "slug": "bitcoin-network-implements-taproot-upgrade",
 123 |       "summary": "First 200 chars of content, stripped of HTML...",
 124 |       "content": "<p>Full HTML content...</p>",
 125 |       "category": "Bitcoin",
 126 |       "tags": ["taproot", "upgrade", "network"],
 127 |       "author": "Protocol Pulse AI",
 128 |       "cover_image_url": "https://images.pexels.com/photos/...",
 129 |       "source_url": "https://...",
 130 |       "source_type": "Bitcoin Magazine",
 131 |       "published_at": "2026-03-04T12:50:56Z",
 132 |       "created_at": "2026-03-04T12:50:56Z",
 133 |       "read_time_minutes": 6
 134 |     }
 135 |   ],
 136 |   "pagination": {
 137 |     "page": 1,
 138 |     "per_page": 20,
 139 |     "total": 1704,
 140 |     "total_pages": 86,
 141 |     "has_next": true,
 142 |     "has_prev": false
 143 |   },
 144 |   "meta": {
 145 |     "generated_at": "2026-03-04T13:00:00Z"
 146 |   }
 147 | }
 148 | ```
 149 | 
 150 | Query parameters:
 151 | - `page` (int, default 1)
 152 | - `per_page` (int, default 20, max 50)
 153 | - `category` (string, filter by category)
 154 | - `search` (string, full-text search on title + content)
 155 | - `since` (ISO datetime, articles after this timestamp)
 156 | - `sort` (string: "newest", "oldest", "popular")
 157 | 
 158 | NOTE: The `content` field is only included on single-article responses (`/api/v2/articles/{slug}`). Listing responses omit it to keep payloads small.
 159 | 
 160 | ### Law 3: No Jinja in the Critical Path
 161 | 
 162 | The Next.js frontend is the only thing visitors see. Jinja templates may remain for admin pages only. No visitor-facing page may be rendered by Jinja. If a Jinja route serves a visitor-facing page, it must redirect to the Next.js equivalent.
 163 | 
 164 | ### Law 4: Every Article Has a Slug
 165 | 
 166 | Every article gets a URL-safe slug derived from its title. The slug is generated at creation time and stored in the database. Article URLs are `/articles/{slug}` not `/articles/{id}`. The slug column must be unique and indexed. Migration script generates slugs for all 1,704 existing articles.
 167 | 
 168 | ### Law 5: Server-Side Rendering for Article Pages
 169 | 
 170 | Individual article pages (`/articles/{slug}`) use Next.js server components to fetch from the Flask API at request time. This guarantees fresh content and proper SEO meta tags (Open Graph, Twitter cards). The listing page (`/articles`) uses ISR (Incremental Static Regeneration, revalidate every 60 seconds) for speed.
 171 | 
 172 | ### Law 6: Pagination is Mandatory
 173 | 
 174 | The article listing page displays 20 articles per page. Pagination is cursor-based in the API but rendered as page numbers in the UI. Infinite scroll is acceptable as an alternative. There is no scenario where all 1,704 articles are fetched at once.
 175 | 
 176 | ### Law 7: Category Filters Work or Don't Exist
 177 | 
 178 | Categories are fetched from `/api/v2/categories` which returns only categories with >0 published articles and their counts. The frontend renders filter pills. Clicking a pill adds `?category=Bitcoin` to the URL and re-fetches. If the filter system is not wired, the pills do not render. No dead UI elements.
 179 | 
 180 | ### Law 8: Mobile-First, Dark-Mode-First
 181 | 
 182 | Protocol Pulse is a Bitcoin intelligence platform. The audience expects dark mode. Design dark-first, light as optional toggle. All layouts are mobile-first with breakpoints at 640px (sm), 768px (md), 1024px (lg), 1280px (xl). Article body text is 18px on desktop, 16px on mobile, max-width 720px, centered.
 183 | 
 184 | ### Law 9: Performance Budget
 185 | 
 186 | | Metric | Target |
 187 | |--------|--------|
 188 | | Largest Contentful Paint | < 2.5s |
 189 | | First Input Delay | < 100ms |
 190 | | Cumulative Layout Shift | < 0.1 |
 191 | | Article listing page size | < 200KB gzipped |
 192 | | Time to Interactive | < 3.5s on 3G |
 193 | 
 194 | Images use Next.js `<Image>` component with automatic WebP conversion and lazy loading. Cover images on cards are 400x225 (16:9). Hero images on article detail are 1200x675.
 195 | 
 196 | ### Law 10: Content Generator Contract
 197 | 
 198 | Every Article() creation path must produce an article with ALL of these fields populated:
 199 | - title (required, non-empty)
 200 | - content (required, non-empty HTML)
 201 | - category (required, from allowed list)
 202 | - cover_image_url (required, valid HTTPS URL or deterministic fallback)
 203 | - author (required, default "Protocol Pulse AI")
 204 | - published (required, boolean)
 205 | - published_at (required if published=True)
 206 | - slug (required, auto-generated from title, unique)
 207 | 
 208 | Any creation path that commits an Article without these fields is a bug. The model's `__init__` or a `pre_commit` hook must enforce this.
 209 | 
 210 | ---
 211 | 
 212 | ## PART 4: THE MIGRATION PLAN
 213 | 
 214 | ### Phase 1: API Layer (Flask Side)
 215 | 
 216 | **Goal:** Build the v2 API endpoints on the existing Flask app so Next.js has something to talk to.
 217 | 
 218 | **Files to create/modify:**
 219 | - `routes_api_v2.py` — New file. Clean API-only routes. No Jinja rendering.
 220 | - `models.py` — Add `slug` column, add `to_api_dict()` method to Article model.
 221 | - `scripts/generate_slugs.py` — One-time migration to generate slugs for all 1,704 articles.
 222 | 
 223 | **Endpoints:**
 224 | 
 225 | ```
 226 | GET  /api/v2/articles          — Paginated article list (no content field)
 227 | GET  /api/v2/articles/{slug}   — Single article by slug (includes content)
 228 | GET  /api/v2/categories        — Categories with counts
 229 | GET  /api/v2/search?q=...      — Full-text search
 230 | GET  /api/v2/prices            — BTC price data (proxy existing price_service)
 231 | ```
 232 | 
 233 | **CORS:** Allow requests from protocolpulse.io and localhost:3000 (dev).
 234 | 
 235 | **Auth:** Public read endpoints. No auth required. Admin endpoints (existing) stay behind token.
 236 | 
 237 | **Claude Code prompt for Phase 1:**
 238 | ```
 239 | tmux new-session -s api-v2 \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
 240 | 
 241 | CONTEXT: Read ARTICLE_PAGE_LAWS.md first. You are building the v2 API layer.
 242 | 
 243 | TASKS:
 244 | 1. Create routes_api_v2.py with 5 endpoints (see Laws doc Part 4 Phase 1)
 245 | 2. Add slug column + to_api_dict() to models.py
 246 | 3. Create scripts/generate_slugs.py for migration
 247 | 4. Register blueprint in app.py
 248 | 5. Add CORS for protocolpulse.io and localhost:3000
 249 | 
 250 | RULES:
 251 | - Do NOT touch existing routes.py
 252 | - Do NOT modify any Jinja templates
 253 | - Response format must EXACTLY match Law 2 schema
 254 | - Listing endpoint omits content field
 255 | - Detail endpoint includes content field
 256 | - Pagination defaults: page=1, per_page=20, max=50
 257 | - Search uses PostgreSQL ILIKE on title + content
 258 | - Every endpoint returns JSON, never HTML
 259 | - Test every endpoint with curl
 260 | - Git add + commit + push when done
 261 | ```
 262 | 
 263 | ### Phase 2: Next.js Frontend
 264 | 
 265 | **Goal:** Build the Next.js app that replaces all Jinja article pages.
 266 | 
 267 | **Project structure:**
 268 | ```
 269 | protocol-pulse-frontend/
 270 | ├── package.json
 271 | ├── next.config.js
 272 | ├── tailwind.config.js
 273 | ├── public/
 274 | │   ├── fonts/
 275 | │   └── images/
 276 | ├── src/
 277 | │   ├── app/
 278 | │   │   ├── layout.tsx          — Root layout (dark mode, nav, footer)
 279 | │   │   ├── page.tsx            — Homepage
 280 | │   │   ├── articles/
 281 | │   │   │   ├── page.tsx        — Article listing (ISR, paginated)
 282 | │   │   │   └── [slug]/
 283 | │   │   │       └── page.tsx    — Article detail (SSR)
 284 | │   │   └── globals.css
 285 | │   ├── components/
 286 | │   │   ├── ArticleCard.tsx     — Card for listing page
 287 | │   │   ├── ArticleBody.tsx     — Rendered article content
 288 | │   │   ├── CategoryFilter.tsx  — Filter pills
 289 | │   │   ├── Pagination.tsx      — Page navigation
 290 | │   │   ├── Navbar.tsx          — Top nav with BTC ticker
 291 | │   │   ├── Footer.tsx          — Site footer
 292 | │   │   ├── SearchBar.tsx       — Article search
 293 | │   │   └── BtcTicker.tsx       — Real-time BTC price
 294 | │   ├── lib/
 295 | │   │   ├── api.ts              — API client (typed fetch wrapper)
 296 | │   │   └── types.ts            — TypeScript interfaces matching Law 2
 297 | │   └── styles/
 298 | │       └── article.css         — Article body typography
 299 | ├── .env.local                  — API_BASE_URL=https://api.protocolpulse.io
 300 | └── vercel.json
 301 | ```
 302 | 
 303 | **Design System (matching top-10 news sites):**
 304 | 
 305 | 1. **Typography:** Inter or system font stack. Article body: 18px/1.7 on desktop. Max-width 720px centered. Generous paragraph spacing (1.5em).
 306 | 
 307 | 2. **Article cards:** 16:9 cover image, title (bold, 20px), category pill, read time, date. On hover: subtle lift shadow. Grid: 1col mobile, 2col tablet, 3col desktop.
 308 | 
 309 | 3. **Article detail:** Full-width hero (1200x675), title below, author + date + read time + category, then content in centered 720px column. Related articles at bottom.
 310 | 
 311 | 4. **Color system:**
 312 |    - Background: #0A0A0A (near-black)
 313 |    - Surface: #141414 (cards, elevated)
 314 |    - Border: #1F1F1F (subtle dividers)
 315 |    - Text primary: #EDEDED
 316 |    - Text secondary: #888888
 317 |    - Accent: #CC0000 (Protocol Pulse red)
 318 |    - Link: #CC0000
 319 | 
 320 | 5. **No visual clutter.** No sidebar on article pages. No ads between paragraphs until Sponsor Agent is activated. Clean reading experience rivaling NYT/Bloomberg.
 321 | 
 322 | **Claude Code prompt for Phase 2:**
 323 | ```
 324 | tmux new-session -s nextjs-build \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
 325 | 
 326 | CONTEXT: Read ARTICLE_PAGE_LAWS.md first. You are building the Next.js frontend.
 327 | 
 328 | TASKS:
 329 | 1. Init Next.js at ~/protocol_pulse/frontend/
 330 |    npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
 331 | 2. Configure tailwind with Protocol Pulse color system
 332 | 3. Build API client (src/lib/api.ts) with typed responses
 333 | 4. Build article listing page with ISR, category filters, pagination
 334 | 5. Build article detail page with SSR, SEO meta, hero image, typography
 335 | 6. Build layout with dark-mode navbar, BTC ticker, footer
 336 | 7. Configure next.config.js remotePatterns for images.pexels.com
 337 | 8. Test on mobile viewport (375px) before done
 338 | 
 339 | DESIGN RULES:
 340 | - Dark first. BG #0A0A0A, surface #141414, accent #CC0000
 341 | - Article body: 18px/1.7, max-width 720px centered
 342 | - Mobile-first. sm:640, md:768, lg:1024, xl:1280
 343 | - No sidebar on article detail
 344 | - Next.js Image component for all images
 345 | - NO localStorage, NO sessionStorage
 346 | - Git add + commit + push when done
 347 | ```
 348 | 
 349 | ### Phase 3: DNS Cutover and Cleanup
 350 | 
 351 | **Steps:**
 352 | 1. Deploy Next.js to Vercel, get preview URL
 353 | 2. Verify all pages render correctly
 354 | 3. Cloudflare DNS: protocolpulse.io CNAME to Vercel, api.protocolpulse.io CNAME to Replit
 355 | 4. Add custom domain in Vercel
 356 | 5. Flask app: redirect old /articles routes to Next.js
 357 | 6. Mark old Jinja routes @deprecated
 358 | 7. Do NOT delete old code for 2 weeks
 359 | 
 360 | ---
 361 | 
 362 | ## PART 5: THE CLEANSE (Post-Migration, After 2 Weeks Stable)
 363 | 
 364 | ### Files to Delete
 365 | - templates/articles.html
 366 | - templates/article_detail.html
 367 | - templates/article_master.html
 368 | 
 369 | ### Code to Remove from routes.py
 370 | - The /articles Jinja route (~lines 1185-1345)
 371 | - The /articles/<int:article_id> Jinja route (~lines 1362-1450)
 372 | - All template rendering for articles
 373 | - article_image_urls dict building logic
 374 | - _article_body_without_tldr helper
 375 | - _article_key_takeaways helper
 376 | 
 377 | ### Code to Consolidate
 378 | All 16 Article() creation paths reduced to 1 factory function:
 379 | 
 380 | ```python
 381 | # services/article_factory.py — SINGLE SOURCE OF TRUTH
 382 | 
 383 | def create_article(title, content, category, source_url, source_type,
 384 |                    cover_image_url=None, author="Protocol Pulse AI",
 385 |                    published=True):
 386 |     """Every article creation in the entire codebase calls this. No exceptions."""
 387 |     slug = generate_unique_slug(title)
 388 | 
 389 |     if not cover_image_url:
 390 |         cover_image_url = fetch_pexels_cover(title) or f"/static/images/default-covers/btc-{hash(slug) % 10}.jpg"
 391 | 
 392 |     article = Article(
 393 |         title=title,
 394 |         slug=slug,
 395 |         content=content,
 396 |         category=category,
 397 |         cover_image_url=cover_image_url,
 398 |         source_url=source_url,
 399 |         source_type=source_type,
 400 |         author=author,
 401 |         published=published,
 402 |         published_at=datetime.utcnow() if published else None,
 403 |     )
 404 |     db.session.add(article)
 405 |     db.session.commit()
 406 |     return article
 407 | ```
 408 | 
 409 | ### Column Cleanup
 410 | - `header_image_url` — DEPRECATED. Delete column after 2 weeks.
 411 | - Audit all 24 columns. Any column NULL on >90% of articles gets removed.
 412 | 
 413 | ---
 414 | 
 415 | ## PART 6: EXECUTION ORDER
 416 | 
 417 | ```
 418 | Week 1: Phase 1 — API Layer
 419 |   Day 1: Build routes_api_v2.py, add slug column, run slug migration
 420 |   Day 2: Test all endpoints, fix edge cases, add CORS
 421 |   Day 3: Deploy to Replit, verify JSON responses from browser
 422 | 
 423 | Week 2: Phase 2 — Next.js Frontend
 424 |   Day 1: Init project, API client, article listing page
 425 |   Day 2: Article detail page, SEO meta, typography
 426 |   Day 3: Nav, footer, category filters, pagination
 427 |   Day 4: Mobile testing, performance audit, polish
 428 |   Day 5: Deploy to Vercel preview
 429 | 
 430 | Week 3: Phase 3 — Cutover
 431 |   Day 1: Final QA on Vercel preview vs current site
 432 |   Day 2: DNS cutover in Cloudflare
 433 |   Day 3: Monitor, fix any issues
 434 | 
 435 | Week 4+: Phase 4 — Cleanse
 436 |   Delete Jinja templates, consolidate 16 creation paths into 1,
 437 |   remove deprecated columns
 438 | ```
 439 | 
 440 | ---
 441 | 
 442 | ## PART 7: BANNED PRACTICES
 443 | 
 444 | Permanently banned from any session touching article code:
 445 | 
 446 | 1. **BANNED: Building new Jinja templates.** The Jinja era is over.
 447 | 2. **BANNED: Adding fallback chains for images.** One column, one source. cover_image_url or bust.
 448 | 3. **BANNED: Writing to header_image_url.** Deprecated. Dead. Gone.
 449 | 4. **BANNED: Direct Article() construction outside create_article().** After cleanse, all paths use the factory.
 450 | 5. **BANNED: Returning HTML from API endpoints.** JSON only.
 451 | 6. **BANNED: Fetching all articles at once.** Pagination is mandatory. Max 50 per request.
 452 | 7. **BANNED: Client-side rendering for article content.** SSR or SSG only. SEO is non-negotiable.
 453 | 8. **BANNED: Adding columns to Article model without updating to_api_dict().** API schema stays in sync.
 454 | 9. **BANNED: Ghost, WordPress, or any paid CMS.** We own our stack.
 455 | 10. **BANNED: Three.js, VR, DAO, quantum auth, Sora, genetic algorithms on article pages.** (Inherited from MEDIA UNIFIED ban list.)
 456 | 
 457 | ---
 458 | 
 459 | ## APPENDIX A: Current Article Model Schema
 460 | 
 461 | ```
 462 | id                  INTEGER PRIMARY KEY
 463 | title               VARCHAR
 464 | content             TEXT
 465 | summary             TEXT
 466 | category            VARCHAR
 467 | tags                VARCHAR (JSON string)
 468 | author              VARCHAR
 469 | source_url          VARCHAR
 470 | source_type         VARCHAR
 471 | header_image_url    VARCHAR  [DEPRECATED — stop writing, delete after migration]
 472 | cover_image_url     VARCHAR  [PRIMARY IMAGE FIELD]
 473 | published           BOOLEAN
 474 | published_at        DATETIME
 475 | created_at          DATETIME
 476 | updated_at          DATETIME
 477 | seo_title           VARCHAR
 478 | seo_description     VARCHAR
 479 | slug                VARCHAR  [TO ADD — Phase 1]
 480 | read_count          INTEGER
 481 | fact_check_passed   BOOLEAN
 482 | grok_review_score   FLOAT
 483 | gemini_review_score FLOAT
 484 | quality_tier        VARCHAR
 485 | content_hash        VARCHAR
 486 | ```
 487 | 
 488 | ## APPENDIX B: The 16 Article Creation Paths (Pre-Cleanse)
 489 | 
 490 | 1. `services/article_automation.py:682` — Main automation cycle
 491 | 2. `services/article_automation.py:938` — Reddit trend generation
 492 | 3. `services/automation.py:290` — Legacy automation
 493 | 4. `services/automation.py:331` — Legacy variant
 494 | 5. `services/automation.py:365` — Stub creation
 495 | 6. `services/automation.py:428` — Another variant
 496 | 7. `services/automation.py:471` — Yet another variant
 497 | 8. `services/affiliate_article_generator.py:405` — Affiliate articles
 498 | 9. `services/affiliate_article_generator.py:439` — Affiliate variant
 499 | 10. `services/briefing_engine.py:121` — Daily briefing
 500 | 11-16. Various paths in routes.py admin endpoints
 501 | 
 502 | **Post-cleanse target: 1 path. `create_article()` in `services/article_factory.py`.**
 503 | 
 504 | ---
 505 | 
 506 | *This document is the single source of truth for all article-related development on Protocol Pulse. Any Claude Code session that modifies article code MUST read this file first. Any decision that contradicts these laws requires explicit PBX approval.*
 507 | 
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
