# Protocol Pulse — Priority Roadmap (Inch by Inch)

**Goal:** Make the site usable and valuable with content publishing, affiliate marketing, and social automation — one step at a time, in order.

---

## Ranked priority (what to do first)

| Rank | Focus | Why first | Success looks like |
|------|--------|-----------|--------------------|
| **1** | **Articles & publishing** | No content = nothing to promote, nothing to monetize. This is the foundation. | Articles appear on the site; new ones can be published without hitting Replit-era blockers; optional: old articles restored if you have a backup. |
| **2** | **Article pipeline (create → publish)** | So you’re not stuck with only manual drafts. | Automation or admin “Publish” reliably creates articles and marks them published on the site (Substack optional). |
| **3** | **Affiliate marketing** | Monetization. Depends on having pages (articles, etc.) to attach links to. | Affiliate links/placements work on key pages; clicks or conversions are trackable where you expect. |
| **4** | **Social media automation** | Distribution. Needs content (articles) to share. | Scheduled or one-click sharing of articles (or briefs) to X/Nostr without 404s or dead flows. |

---

## Priority 1: Articles & publishing (do this first)

**Problems to fix:**

- **“Articles not publishing”** — Current flow ties “published on site” to AI review + Substack success. If Substack or API keys fail, the article may never get `published=True` and never show on the site.
- **“Old articles gone”** — Replit DB wasn’t migrated; the current DB starts empty. Restoring old articles only works if we have a backup (export from Replit or a dump file).

**Concrete steps (in order):**

1. **Unblock “publish on site”**
   - When an article is approved (or when you click Publish in admin), set `published=True` and commit **so it always shows on the site**, even if Substack (or another external step) fails.
   - Optional: add a “Publish on site only” path that skips Substack so the site works without Substack configured.

2. **Verify article listing and detail pages**
   - Confirm `/articles`, category pages, and article detail pages only show articles with `published=True` and that they load without errors.

3. **Restore old articles (if you have data)**
   - If you have a Replit export (SQLite file, SQL dump, or CSV of articles): we add a one-time import script (or admin action) to load that into the current DB so old articles appear again.
   - If you don’t have a backup: we can’t recreate lost data; we focus on making all new articles publish reliably.

4. **Diagnose automation**
   - Run the existing article-generation path (e.g. ContentEngine → ContentGenerator → Reddit fallback) once, capture errors (missing keys, exceptions). Fix the first blocking issue so at least one path can create and publish an article.

---

## Priority 2: Article pipeline (create → publish)

- Trigger article generation (admin button or scheduler) and confirm articles are created and saved with `published=True` when appropriate.
- Ensure “Publish” in admin always results in the article being visible on the site, with or without Substack.

---

## Priority 3: Affiliate marketing

- Identify which pages should carry affiliate links (e.g. articles, guides, product pages).
- Verify affiliate product/link config and click tracking (e.g. `AffiliateProduct`, `AffiliateProductClick`, monetization engine) and fix one flow end-to-end (e.g. one product, one page).

---

## Priority 4: Social media automation

- Fix any 404s or broken routes for the social/Megaphone flows (already addressed in recent wiring).
- Ensure one path works: e.g. “share this article” or “post this brief” to X or Nostr without errors.

---

## How we’ll work from here

- **One slice at a time:** We’ll take the next step from the table above (starting with 1.1), implement it, and only then move on.
- **Verify before moving on:** Each step ends with a quick check (e.g. “publish an article and see it on /articles”).
- **No big redesigns:** Changes will be minimal and targeted so the site stays stable while we fix the essentials.

Next recommended action: **Priority 1, Step 1 — Unblock “publish on site”** so that when you publish an article (or automation creates one), it always shows on the site even if Substack or another external service fails.
