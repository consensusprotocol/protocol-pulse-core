# ARTICLE PAGE LAWS v1.0

## Protocol Pulse — Article Frontend Migration Spec

**Status:** GOSPEL. Load this into EVERY Claude Code session touching article code.
**Created:** 2026-03-04
**Authority:** PBX + Claude Opus forensic audit

---

## PART 1: THE DAMAGE REPORT (Forensic Audit Findings)

### What We Found

| Problem | Evidence |
|---------|----------|
| Jinja template sprawl | 2,539 lines across 3 files: articles.html, article_detail.html, article_master.html |
| Monolith route file | 8,472 lines in routes.py — one file handling everything |
| Article creation chaos | 16 different Article() creation paths across 6 files |
| Cover image failures | cover_image_url not set by content generator; 183 articles published without images before manual backfill |
| Useless API | Only public JSON endpoint is /api/latest-articles — returns 6 articles with 4 fields |
| No pagination | 1,704 articles, only 40 displayed. No load-more, no page numbers, no infinite scroll |
| Dead category filters | 19 categories in DB, filter UI exists but non-functional |
| Column sprawl | 24 database columns on Article model, many unused or redundant |
| Dual image columns | Both header_image_url (local PIL files) and cover_image_url (Pexels URLs) — generator writes to one, template reads the other |

### Root Cause

The Flask/Jinja frontend was built incrementally by AI agents over months. Each agent added features without understanding the full system. Result: 16 creation paths where each one handles images differently, a route file no human or AI can reason about, and templates that paper over backend inconsistencies with 5 layers of fallback logic.

**Verdict: The Jinja frontend is unreformable. We replace it.**

---

## PART 2: THE ARCHITECTURE

### Target Stack (Zero Additional Cost)

```
┌─────────────────────────────────────────────────┐
│                    VISITORS                       │
│              protocolpulse.io                     │
└────────────────────┬────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │    Next.js Frontend   │
          │   (Vercel, free tier) │
          │                       │
          │  React components     │
          │  Server-side render   │
          │  Static generation    │
          │  Image optimization   │
          │  Built-in pagination  │
          └──────────┬───────────┘
                     │ JSON API calls
          ┌──────────▼──────────┐
          │    Flask API Layer    │
          │  (Replit, existing)   │
          │                       │
          │  /api/v2/articles     │
          │  /api/v2/categories   │
          │  /api/v2/search       │
          │  /api/v2/prices       │
          └──────────┬───────────┘
                     │
          ┌──────────▼──────────┐
          │     PostgreSQL        │
          │  (Replit, existing)   │
          │                       │
          │  1,704 articles       │
          │  All cover images     │
          │  Categories, tags     │
          └──────────────────────┘

          ┌──────────────────────┐
          │   Ultron (unchanged)  │
          │                       │
          │  Video pipeline       │
          │  Avatar system        │
          │  Claude Code sessions │
          │  Git push origin      │
          └──────────────────────┘
```

### What Changes vs. What Stays

| Component | Action |
|-----------|--------|
| PostgreSQL database | STAYS. Zero changes. |
| Article content generator | STAYS. Only change: guaranteed cover_image_url on every new article (already patched). |
| Flask app on Replit | STAYS as API-only backend. Jinja templates get deprecated, not deleted (keep for admin). |
| routes.py article routes | REPLACED by 3 clean API endpoints. Old Jinja routes marked @deprecated. |
| Jinja templates (articles.html etc.) | RETIRED. Replaced by Next.js React pages. |
| Ultron pipeline | UNCHANGED. Zero touches. |
| Cloudflare DNS | UPDATE: protocolpulse.io points to Vercel. API subdomain api.protocolpulse.io points to Replit. |
| Video pipeline, tweet system, Oracle Briefings | UNCHANGED. |

---

## PART 3: THE LAWS

These are permanent. Every session must obey them.

### Law 1: One Source of Truth for Article Images

The column is `cover_image_url`. Period. It contains a full HTTPS Pexels URL.
- `header_image_url` is DEPRECATED. Never read it, never write it in new code.
- Every Article() creation path MUST set cover_image_url before commit.
- If Pexels fails, set cover_image_url to a deterministic fallback: `/static/images/default-covers/btc-{article_id % 10}.jpg` (10 pre-generated default images).
- The API never returns header_image_url. Only cover_image_url.

### Law 2: One API, One Schema

All article data flows through `/api/v2/articles`. The response schema is:

```json
{
  "articles": [
    {
      "id": 1874,
      "title": "Bitcoin Network Implements Taproot Upgrade",
      "slug": "bitcoin-network-implements-taproot-upgrade",
      "summary": "First 200 chars of content, stripped of HTML...",
      "content": "<p>Full HTML content...</p>",
      "category": "Bitcoin",
      "tags": ["taproot", "upgrade", "network"],
      "author": "Protocol Pulse AI",
      "cover_image_url": "https://images.pexels.com/photos/...",
      "source_url": "https://...",
      "source_type": "Bitcoin Magazine",
      "published_at": "2026-03-04T12:50:56Z",
      "created_at": "2026-03-04T12:50:56Z",
      "read_time_minutes": 6
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1704,
    "total_pages": 86,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "generated_at": "2026-03-04T13:00:00Z"
  }
}
```

Query parameters:
- `page` (int, default 1)
- `per_page` (int, default 20, max 50)
- `category` (string, filter by category)
- `search` (string, full-text search on title + content)
- `since` (ISO datetime, articles after this timestamp)
- `sort` (string: "newest", "oldest", "popular")

NOTE: The `content` field is only included on single-article responses (`/api/v2/articles/{slug}`). Listing responses omit it to keep payloads small.

### Law 3: No Jinja in the Critical Path

The Next.js frontend is the only thing visitors see. Jinja templates may remain for admin pages only. No visitor-facing page may be rendered by Jinja. If a Jinja route serves a visitor-facing page, it must redirect to the Next.js equivalent.

### Law 4: Every Article Has a Slug

Every article gets a URL-safe slug derived from its title. The slug is generated at creation time and stored in the database. Article URLs are `/articles/{slug}` not `/articles/{id}`. The slug column must be unique and indexed. Migration script generates slugs for all 1,704 existing articles.

### Law 5: Server-Side Rendering for Article Pages

Individual article pages (`/articles/{slug}`) use Next.js server components to fetch from the Flask API at request time. This guarantees fresh content and proper SEO meta tags (Open Graph, Twitter cards). The listing page (`/articles`) uses ISR (Incremental Static Regeneration, revalidate every 60 seconds) for speed.

### Law 6: Pagination is Mandatory

The article listing page displays 20 articles per page. Pagination is cursor-based in the API but rendered as page numbers in the UI. Infinite scroll is acceptable as an alternative. There is no scenario where all 1,704 articles are fetched at once.

### Law 7: Category Filters Work or Don't Exist

Categories are fetched from `/api/v2/categories` which returns only categories with >0 published articles and their counts. The frontend renders filter pills. Clicking a pill adds `?category=Bitcoin` to the URL and re-fetches. If the filter system is not wired, the pills do not render. No dead UI elements.

### Law 8: Mobile-First, Dark-Mode-First

Protocol Pulse is a Bitcoin intelligence platform. The audience expects dark mode. Design dark-first, light as optional toggle. All layouts are mobile-first with breakpoints at 640px (sm), 768px (md), 1024px (lg), 1280px (xl). Article body text is 18px on desktop, 16px on mobile, max-width 720px, centered.

### Law 9: Performance Budget

| Metric | Target |
|--------|--------|
| Largest Contentful Paint | < 2.5s |
| First Input Delay | < 100ms |
| Cumulative Layout Shift | < 0.1 |
| Article listing page size | < 200KB gzipped |
| Time to Interactive | < 3.5s on 3G |

Images use Next.js `<Image>` component with automatic WebP conversion and lazy loading. Cover images on cards are 400x225 (16:9). Hero images on article detail are 1200x675.

### Law 10: Content Generator Contract

Every Article() creation path must produce an article with ALL of these fields populated:
- title (required, non-empty)
- content (required, non-empty HTML)
- category (required, from allowed list)
- cover_image_url (required, valid HTTPS URL or deterministic fallback)
- author (required, default "Protocol Pulse AI")
- published (required, boolean)
- published_at (required if published=True)
- slug (required, auto-generated from title, unique)

Any creation path that commits an Article without these fields is a bug. The model's `__init__` or a `pre_commit` hook must enforce this.

---

## PART 4: THE MIGRATION PLAN

### Phase 1: API Layer (Flask Side)

**Goal:** Build the v2 API endpoints on the existing Flask app so Next.js has something to talk to.

**Files to create/modify:**
- `routes_api_v2.py` — New file. Clean API-only routes. No Jinja rendering.
- `models.py` — Add `slug` column, add `to_api_dict()` method to Article model.
- `scripts/generate_slugs.py` — One-time migration to generate slugs for all 1,704 articles.

**Endpoints:**

```
GET  /api/v2/articles          — Paginated article list (no content field)
GET  /api/v2/articles/{slug}   — Single article by slug (includes content)
GET  /api/v2/categories        — Categories with counts
GET  /api/v2/search?q=...      — Full-text search
GET  /api/v2/prices            — BTC price data (proxy existing price_service)
```

**CORS:** Allow requests from protocolpulse.io and localhost:3000 (dev).

**Auth:** Public read endpoints. No auth required. Admin endpoints (existing) stay behind token.

**Claude Code prompt for Phase 1:**
```
tmux new-session -s api-v2 \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter

CONTEXT: Read ARTICLE_PAGE_LAWS.md first. You are building the v2 API layer.

TASKS:
1. Create routes_api_v2.py with 5 endpoints (see Laws doc Part 4 Phase 1)
2. Add slug column + to_api_dict() to models.py
3. Create scripts/generate_slugs.py for migration
4. Register blueprint in app.py
5. Add CORS for protocolpulse.io and localhost:3000

RULES:
- Do NOT touch existing routes.py
- Do NOT modify any Jinja templates
- Response format must EXACTLY match Law 2 schema
- Listing endpoint omits content field
- Detail endpoint includes content field
- Pagination defaults: page=1, per_page=20, max=50
- Search uses PostgreSQL ILIKE on title + content
- Every endpoint returns JSON, never HTML
- Test every endpoint with curl
- Git add + commit + push when done
```

### Phase 2: Next.js Frontend

**Goal:** Build the Next.js app that replaces all Jinja article pages.

**Project structure:**
```
protocol-pulse-frontend/
├── package.json
├── next.config.js
├── tailwind.config.js
├── public/
│   ├── fonts/
│   └── images/
├── src/
│   ├── app/
│   │   ├── layout.tsx          — Root layout (dark mode, nav, footer)
│   │   ├── page.tsx            — Homepage
│   │   ├── articles/
│   │   │   ├── page.tsx        — Article listing (ISR, paginated)
│   │   │   └── [slug]/
│   │   │       └── page.tsx    — Article detail (SSR)
│   │   └── globals.css
│   ├── components/
│   │   ├── ArticleCard.tsx     — Card for listing page
│   │   ├── ArticleBody.tsx     — Rendered article content
│   │   ├── CategoryFilter.tsx  — Filter pills
│   │   ├── Pagination.tsx      — Page navigation
│   │   ├── Navbar.tsx          — Top nav with BTC ticker
│   │   ├── Footer.tsx          — Site footer
│   │   ├── SearchBar.tsx       — Article search
│   │   └── BtcTicker.tsx       — Real-time BTC price
│   ├── lib/
│   │   ├── api.ts              — API client (typed fetch wrapper)
│   │   └── types.ts            — TypeScript interfaces matching Law 2
│   └── styles/
│       └── article.css         — Article body typography
├── .env.local                  — API_BASE_URL=https://api.protocolpulse.io
└── vercel.json
```

**Design System (matching top-10 news sites):**

1. **Typography:** Inter or system font stack. Article body: 18px/1.7 on desktop. Max-width 720px centered. Generous paragraph spacing (1.5em).

2. **Article cards:** 16:9 cover image, title (bold, 20px), category pill, read time, date. On hover: subtle lift shadow. Grid: 1col mobile, 2col tablet, 3col desktop.

3. **Article detail:** Full-width hero (1200x675), title below, author + date + read time + category, then content in centered 720px column. Related articles at bottom.

4. **Color system:**
   - Background: #0A0A0A (near-black)
   - Surface: #141414 (cards, elevated)
   - Border: #1F1F1F (subtle dividers)
   - Text primary: #EDEDED
   - Text secondary: #888888
   - Accent: #CC0000 (Protocol Pulse red)
   - Link: #CC0000

5. **No visual clutter.** No sidebar on article pages. No ads between paragraphs until Sponsor Agent is activated. Clean reading experience rivaling NYT/Bloomberg.

**Claude Code prompt for Phase 2:**
```
tmux new-session -s nextjs-build \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter

CONTEXT: Read ARTICLE_PAGE_LAWS.md first. You are building the Next.js frontend.

TASKS:
1. Init Next.js at ~/protocol_pulse/frontend/
   npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
2. Configure tailwind with Protocol Pulse color system
3. Build API client (src/lib/api.ts) with typed responses
4. Build article listing page with ISR, category filters, pagination
5. Build article detail page with SSR, SEO meta, hero image, typography
6. Build layout with dark-mode navbar, BTC ticker, footer
7. Configure next.config.js remotePatterns for images.pexels.com
8. Test on mobile viewport (375px) before done

DESIGN RULES:
- Dark first. BG #0A0A0A, surface #141414, accent #CC0000
- Article body: 18px/1.7, max-width 720px centered
- Mobile-first. sm:640, md:768, lg:1024, xl:1280
- No sidebar on article detail
- Next.js Image component for all images
- NO localStorage, NO sessionStorage
- Git add + commit + push when done
```

### Phase 3: DNS Cutover and Cleanup

**Steps:**
1. Deploy Next.js to Vercel, get preview URL
2. Verify all pages render correctly
3. Cloudflare DNS: protocolpulse.io CNAME to Vercel, api.protocolpulse.io CNAME to Replit
4. Add custom domain in Vercel
5. Flask app: redirect old /articles routes to Next.js
6. Mark old Jinja routes @deprecated
7. Do NOT delete old code for 2 weeks

---

## PART 5: THE CLEANSE (Post-Migration, After 2 Weeks Stable)

### Files to Delete
- templates/articles.html
- templates/article_detail.html
- templates/article_master.html

### Code to Remove from routes.py
- The /articles Jinja route (~lines 1185-1345)
- The /articles/<int:article_id> Jinja route (~lines 1362-1450)
- All template rendering for articles
- article_image_urls dict building logic
- _article_body_without_tldr helper
- _article_key_takeaways helper

### Code to Consolidate
All 16 Article() creation paths reduced to 1 factory function:

```python
# services/article_factory.py — SINGLE SOURCE OF TRUTH

def create_article(title, content, category, source_url, source_type,
                   cover_image_url=None, author="Protocol Pulse AI",
                   published=True):
    """Every article creation in the entire codebase calls this. No exceptions."""
    slug = generate_unique_slug(title)

    if not cover_image_url:
        cover_image_url = fetch_pexels_cover(title) or f"/static/images/default-covers/btc-{hash(slug) % 10}.jpg"

    article = Article(
        title=title,
        slug=slug,
        content=content,
        category=category,
        cover_image_url=cover_image_url,
        source_url=source_url,
        source_type=source_type,
        author=author,
        published=published,
        published_at=datetime.utcnow() if published else None,
    )
    db.session.add(article)
    db.session.commit()
    return article
```

### Column Cleanup
- `header_image_url` — DEPRECATED. Delete column after 2 weeks.
- Audit all 24 columns. Any column NULL on >90% of articles gets removed.

---

## PART 6: EXECUTION ORDER

```
Week 1: Phase 1 — API Layer
  Day 1: Build routes_api_v2.py, add slug column, run slug migration
  Day 2: Test all endpoints, fix edge cases, add CORS
  Day 3: Deploy to Replit, verify JSON responses from browser

Week 2: Phase 2 — Next.js Frontend
  Day 1: Init project, API client, article listing page
  Day 2: Article detail page, SEO meta, typography
  Day 3: Nav, footer, category filters, pagination
  Day 4: Mobile testing, performance audit, polish
  Day 5: Deploy to Vercel preview

Week 3: Phase 3 — Cutover
  Day 1: Final QA on Vercel preview vs current site
  Day 2: DNS cutover in Cloudflare
  Day 3: Monitor, fix any issues

Week 4+: Phase 4 — Cleanse
  Delete Jinja templates, consolidate 16 creation paths into 1,
  remove deprecated columns
```

---

## PART 7: BANNED PRACTICES

Permanently banned from any session touching article code:

1. **BANNED: Building new Jinja templates.** The Jinja era is over.
2. **BANNED: Adding fallback chains for images.** One column, one source. cover_image_url or bust.
3. **BANNED: Writing to header_image_url.** Deprecated. Dead. Gone.
4. **BANNED: Direct Article() construction outside create_article().** After cleanse, all paths use the factory.
5. **BANNED: Returning HTML from API endpoints.** JSON only.
6. **BANNED: Fetching all articles at once.** Pagination is mandatory. Max 50 per request.
7. **BANNED: Client-side rendering for article content.** SSR or SSG only. SEO is non-negotiable.
8. **BANNED: Adding columns to Article model without updating to_api_dict().** API schema stays in sync.
9. **BANNED: Ghost, WordPress, or any paid CMS.** We own our stack.
10. **BANNED: Three.js, VR, DAO, quantum auth, Sora, genetic algorithms on article pages.** (Inherited from MEDIA UNIFIED ban list.)

---

## APPENDIX A: Current Article Model Schema

```
id                  INTEGER PRIMARY KEY
title               VARCHAR
content             TEXT
summary             TEXT
category            VARCHAR
tags                VARCHAR (JSON string)
author              VARCHAR
source_url          VARCHAR
source_type         VARCHAR
header_image_url    VARCHAR  [DEPRECATED — stop writing, delete after migration]
cover_image_url     VARCHAR  [PRIMARY IMAGE FIELD]
published           BOOLEAN
published_at        DATETIME
created_at          DATETIME
updated_at          DATETIME
seo_title           VARCHAR
seo_description     VARCHAR
slug                VARCHAR  [TO ADD — Phase 1]
read_count          INTEGER
fact_check_passed   BOOLEAN
grok_review_score   FLOAT
gemini_review_score FLOAT
quality_tier        VARCHAR
content_hash        VARCHAR
```

## APPENDIX B: The 16 Article Creation Paths (Pre-Cleanse)

1. `services/article_automation.py:682` — Main automation cycle
2. `services/article_automation.py:938` — Reddit trend generation
3. `services/automation.py:290` — Legacy automation
4. `services/automation.py:331` — Legacy variant
5. `services/automation.py:365` — Stub creation
6. `services/automation.py:428` — Another variant
7. `services/automation.py:471` — Yet another variant
8. `services/affiliate_article_generator.py:405` — Affiliate articles
9. `services/affiliate_article_generator.py:439` — Affiliate variant
10. `services/briefing_engine.py:121` — Daily briefing
11-16. Various paths in routes.py admin endpoints

**Post-cleanse target: 1 path. `create_article()` in `services/article_factory.py`.**

---

*This document is the single source of truth for all article-related development on Protocol Pulse. Any Claude Code session that modifies article code MUST read this file first. Any decision that contradicts these laws requires explicit PBX approval.*
