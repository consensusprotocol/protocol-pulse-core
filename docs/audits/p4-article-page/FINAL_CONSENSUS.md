# CONSENSUS REPORT — P4-ARTICLE-PAGE — CYCLE 2
Generated: 2026-03-09 18:55
Models: grok, gpt4o (+1 failed: gemini — API key revoked)

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Correctness     | N/A    | 0/10   | 0/10 | **0/10**  |
| Law Compliance  | N/A    | 0/10   | 0/10 | **0/10**  |
| Security        | N/A    | 1/10   | 0/10 | **0/10**  |
| Frontend Quality| N/A    | 0/10   | 0/10 | **0/10**  |
| Backend Quality | N/A    | 0/10   | 0/10 | **0/10**  |
| **Overall**     | N/A    | 0/10   | 0/10 | **0/10**  |

> **Scoring note:** Gemini failed with a 403 PERMISSION_DENIED error (leaked API key). Consensus is drawn from 2 of 3 models. The 2-model agreement is effectively unanimous for this cycle. GPT-4o awarded Security 1/10 rather than 0/10 on the grounds that nothing harmful was shipped — not because any security controls exist. Grok downgraded to 0/10 after identifying the broader absence of security specifications. Consensus resolves to 0/10 because the feature is unimplemented and no security measures exist in any form.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — Feature Is Entirely Unimplemented
**What it is:** The repository contains exactly two files: `.gitignore` and `ARTICLE_PAGE_LAWS.md`. No API routes, no model definitions, no database migrations, no Next.js components, no redirect logic, no tests, and no static assets exist.
**Files affected:** Entire feature directory.
**What to change:** Implement the feature as specified in `ARTICLE_PAGE_LAWS.md` Phase 1 through Phase 4. This is the root blocker for every other finding.

### U2 — `.gitignore` Globally Blocks Required Static Assets
**What it is:** `.gitignore` lines 15–16 ignore all `*.png` and `*.jpg` files globally. Law 1 (`ARTICLE_PAGE_LAWS.md:108–110`) requires deterministic fallback cover images at `/static/images/default-covers/btc-{n}.jpg`. Those files can never be committed under current ignore rules.
**File/line:** `.gitignore:15–16` vs `ARTICLE_PAGE_LAWS.md:109`
**What to change:** Scope image ignore rules to specific directories (e.g., `uploads/`, `tmp/`) and whitelist the required static asset path with a negation rule such as `!static/images/default-covers/*.jpg`.

### U3 — No Rate Limiting Specified or Implemented for Public Endpoints
**What it is:** `ARTICLE_PAGE_LAWS.md:223–235` describes public unauthenticated read endpoints expected to serve significant traffic with no mention of throttling, request limits, or caching strategy. Both models independently flagged this as an unacceptable gap.
**File/line:** `ARTICLE_PAGE_LAWS.md:223–235`
**What to change:** Add explicit rate limiting requirements to the spec and implement them in the API layer (e.g., Flask-Limiter or reverse-proxy-level throttling). Define limits per IP, per endpoint, and per time window before any endpoint goes live.

### U4 — Pagination Contract Is Self-Contradictory
**What it is:** The spec defines `page` and `per_page` query parameters with a `total_pages`/`has_next`/`has_prev` response schema (`ARTICLE_PAGE_LAWS.md:136–143`, `150–157`), which is classic offset/page-number pagination. Law 6 (`ARTICLE_PAGE_LAWS.md:172–175`) then states "Pagination is cursor-based in the API but rendered as page numbers in the UI." These two designs are mutually exclusive at the API layer.
**File/line:** `ARTICLE_PAGE_LAWS.md:136–143`, `150–157`, `172–175`
**What to change:** Make a single unambiguous decision before any code is written. Either the API is page-number-based (simplest, consistent with the schema example) or cursor-based (more scalable, but requires a different schema). Remove the contradicting statement and update all examples to match.

### U5 — Fallback Image Algorithm Is Inconsistent Across the Spec
**What it is:** Law 1 specifies the fallback as `btc-{article_id % 10}.jpg` (`ARTICLE_PAGE_LAWS.md:108–110`). The factory example specifies `btc-{hash(slug) % 10}.jpg` (`ARTICLE_PAGE_LAWS.md:389–390`). These produce different results for the same article depending on which code path is followed.
**File/line:** `ARTICLE_PAGE_LAWS.md:109` vs `389–390`
**What to change:** Choose exactly one deterministic algorithm, document it in Law 1 as the canonical source of truth, and delete or align the factory example to match.

---

## MAJORITY FINDINGS (both models agree — 2 of 2)

Given only two active models this cycle, every finding above is already unanimous. The following are findings where one model led and the other explicitly affirmed agreement, placing them at high-confidence majority status:

### M1 — Input Validation for Query Parameters Not Specified
Both models agreed the API contract needs explicit validation rules for `page`, `per_page`, `sort`, `since`, `category`, and `search` query parameters, including valid ranges, type enforcement, and defined error responses for invalid inputs.
**File/line:** `ARTICLE_PAGE_LAWS.md:150–157`, `256`

### M2 — Redirect Semantics (301 vs 302) Not Defined for Old Routes
Both models flagged that Phase 3 / Law 3 requires old Jinja/Flask article routes to redirect to Next.js (`ARTICLE_PAGE_LAWS.md:162`, `356–357`), but the HTTP redirect type is never specified. For SEO preservation and canonicalization, 301 (permanent) is almost certainly required, but this must be explicit.
**File/line:** `ARTICLE_PAGE_LAWS.md:162`, `356–357`

### M3 — No Testing Strategy Defined Anywhere in the Spec
Both models observed that despite a detailed execution order (`ARTICLE_PAGE_LAWS.md:416–438`), the spec contains zero requirements for unit tests, integration tests, or end-to-end tests. For a migration affecting 1,704 existing records and a complete rendering-stack change, this is a critical planning gap.
**File/line:** `ARTICLE_PAGE_LAWS.md:416–438`

### M4 — Slug Collision Handling During Migration Is Unspecified
Both models noted that Law 4 requires unique slugs (`ARTICLE_PAGE_LAWS.md:166`) and `generate_unique_slug(title)` is referenced (`ARTICLE_PAGE_LAWS.md:387`), but the spec provides no deterministic behavior for duplicate titles among existing records. With 1,704 articles to migrate, collisions are probable and the resolution algorithm must be defined before migration runs.
**File/line:** `ARTICLE_PAGE_LAWS.md:166`, `387`

---

## UNIQUE INSIGHTS (single model — evaluate carefully)

### GPT-4o Unique: Law 1 vs Banned Practice #2 Contradiction
**Finding:** Law 1 requires a fallback image (`ARTICLE_PAGE_LAWS.md:109`). Banned Practice #2 prohibits "fallback chains for images" (`ARTICLE_PAGE_LAWS.md:447`). These are textually in tension.
**Assessment: Implement (clarification only, no code change needed).** The intended meaning of Banned Practice #2 is almost certainly "do not implement multi-column or multi-source fallback chains" (e.g., try Pexels → try S3 → try local → use placeholder). A single deterministic fallback is not a chain. The spec should add one clarifying sentence to Banned Practice #2 explicitly permitting the single deterministic fallback mandated by Law 1.

### GPT-4o Unique: Law 2 Schema Example Includes `content` But Listing Omits It
**Finding:** The JSON example at `ARTICLE_PAGE_LAWS.md:124` includes the `content` field, but `ARTICLE_PAGE_LAWS.md:158` states that listing responses omit `content` and only detail responses include it. The single example misleads implementers about which payload belongs to which endpoint.
**Assessment: Implement (low effort, high clarity value).** Provide two separate example payloads — one for list response (without `content`) and one for detail response (with `content`). This prevents a common class of over-fetching bugs.

### GPT-4o Unique: Search Contract Split Across Two Endpoints
**Finding:** Law 2 routes search through `/api/v2/articles?search=` (`ARTICLE_PAGE_LAWS.md:114`, `154`). Phase 1 also defines a separate `GET /api/v2/search?q=` endpoint (`ARTICLE_PAGE_LAWS.md:229`). This potentially violates the "One API, One Schema" principle and creates ambiguity about which endpoint the frontend should call.
**Assessment: Implement (must resolve before code is written).** Decide whether search is a filter on `/api/v2/articles` or a dedicated endpoint. If both legitimately exist for different purposes (e.g., full-text vs. filtered browse), document the distinction explicitly and ensure the frontend only uses one path for article search.

### GPT-4o Unique: Fallback Path Is Relative, But Law 10 Requires HTTPS URL
**Finding:** Law 10 requires `cover_image_url` to be a "valid HTTPS URL or deterministic fallback" (`ARTICLE_PAGE_LAWS.md:202`). Law 1's fallback path `/static/images/default-covers/...` (`ARTICLE_PAGE_LAWS.md:109`) is a relative path, not an HTTPS URL.
**Assessment: Investigate further.** If the frontend constructs absolute URLs from a base domain (standard practice), this is not a runtime bug. However, if the API serializes and returns the raw relative path and consumers treat it as an HTTPS URL, it will break in non-browser contexts (RSS feeds, third-party consumers, OG image tags). The spec should clarify whether the API returns the full absolute URL or the relative path, and Law 10 should be updated to reflect whichever is authoritative.

### Grok Unique: Missing Security Specifications (Input Sanitization, CSP, XSS Headers)
**Finding:** Beyond rate limiting (captured in U3), the spec lacks any mention of input sanitization for the `search` parameter (SQL injection / ILIKE injection risk given PostgreSQL usage), Content-Security-Policy headers, or other XSS mitigations for the Next.js frontend.
**Assessment: Implement.** These are standard requirements for any public-facing web API and frontend. The spec should explicitly mandate input sanitization on all user-supplied query parameters and require security headers to be configured in the Next.js deployment. These are not optional for a production system.

### Grok Unique: ISR 60-Second Revalidation May Produce Stale Data for Time-Sensitive Content
**Finding:** ISR revalidation is set to 60 seconds (`ARTICLE_PAGE_LAWS.md:170`). For a Bitcoin intelligence platform where market-relevant content could be published urgently, a 60-second staleness window may be unacceptable.
**Assessment: Investigate further.** This is a design judgment call, not a correctness bug. The spec should document the rationale for 60 seconds and define an on-demand revalidation escape hatch (Next.js supports `revalidatePath`/`revalidateTag`) for use when articles need immediate propagation. Without implementation, this cannot be scored as a defect, but it warrants a design decision record.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1: Security Score — 1/10 (GPT-4o) vs 0/10 (Grok)
**GPT-4o position:** Awarded 1/10 because nothing harmful was deployed. An unimplemented feature cannot have active vulnerabilities.
**Grok position:** Scored 0/10 because the planning document itself fails to specify security requirements, and a spec that ships to implementation without security requirements is itself a security failure.
**Tiebreaker verdict: Grok is correct for planning purposes.** The consensus score is 0/10. A spec that mandates implementation without security controls is not neutral — it is a blueprint for an insecure system. The appropriate score reflects the total absence of security design, not the absence of deployed risk.

### Conflict 2: Database Backend Contradiction (SQLite vs PostgreSQL)
**GPT-4o position:** Could not confirm the SQLite reference from the provided files; treated the PostgreSQL coupling as the dominant documented fact.
**Grok position:** Flagged the SQLite vs PostgreSQL contradiction as a significant spec inconsistency.
**Tiebreaker verdict: GPT-4o is more precise.** From the artifacts provided, the spec clearly specifies PostgreSQL with ILIKE search (`ARTICLE_PAGE_LAWS.md:67–72`, `89–92`, `257`). If SQLite is referenced elsewhere in the broader codebase, that is a legitimate concern, but it cannot be confirmed from the provided files. The correct action is to note PostgreSQL as the authoritative target and flag any SQLite references in the wider codebase for resolution during implementation.

### Conflict 3: "Spec is Conceptually Sound" (Grok Cycle 1) vs "Too Many Contradictions to Call It Sound" (GPT-4o)
**Tiebreaker verdict: GPT-4o is correct.** A spec with four documented internal contradictions (pagination model, image fallback algorithm, database backend ambiguity, Law 1 vs Banned Practice #2) is not "conceptually sound" as an implementation guide. It will produce divergent implementations. The spec requires revision before it can serve as a reliable contract.

---

## VALIDATED STRENGTHS (do NOT change these)

Both models reviewed the specification document and found no areas of implementation to praise — because no implementation exists. The following are relative strengths within the spec document itself:

- **Migration phasing approach** (`ARTICLE_PAGE_LAWS.md:416–438`): The four-phase execution order (DB migration → API → Frontend → Cutover) is logically sequenced and reflects sound engineering practice. Do not reorder the phases.
- **The 10-Law structure as a governance mechanism**: Using named laws with explicit banned practices is a strong pattern for enforcing architectural consistency. The structure should be retained; only the contradictory content within it needs correction.
- **SEO-first design intent**: The requirement for SSR on article detail pages and ISR on listing pages reflects correct reasoning about crawlability and performance. Do not change this rendering strategy.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Finding |
|-----|--------|---------|
| Law 1 — Single Cover Image Source | ❌ VIOLATED | Conflicts with Banned Practice #2 (needs clarification); fallback algorithm contradicts factory example |
| Law 2 — One API, One Schema | ❌ VIOLATED | Separate `/api/v2/search` endpoint contradicts single-API principle; schema example conflates list and detail payloads |
| Law 3 — Legacy Routes Must Redirect | ❌ NOT IMPLEMENTED | No redirect code exists; redirect type (301/302) unspecified |
| Law 4 — Slugs Are Canonical | ❌ NOT IMPLEMENTED | No slug generation code; collision resolution unspecified for migration |
| Law 5 — No Direct DB from Frontend | ❌ NOT IMPLEMENTED | No frontend exists to evaluate |
| Law 6 — Pagination Model | ❌ SELF-CONTRADICTORY | Page-number schema conflicts with cursor-based claim |
| Law 7 — ISR for Listings, SSR for Detail | ❌ NOT IMPLEMENTED | No frontend exists |
| Law 8 — Category Filter Is Additive | ❌ NOT IMPLEMENTED | No filter logic exists |
| Law 9 — Search Is PostgreSQL ILIKE | ❌ NOT IMPLEMENTED | No search implementation |
| Law 10 — Cover URL Validation | ❌ AMBIGUOUS | Relative fallback path may not satisfy "valid HTTPS URL" requirement |

**Determination: 0 of 10 laws are fully compliant. 3 laws have internal spec contradictions that must be resolved before implementation can even begin (Laws 1, 2, 6).**

---

## SECURITY CONSENSUS

Both models identified security gaps. Priority order by consensus severity:

1. **No rate limiting on public endpoints** (both models) — Public unauthenticated API endpoints with no throttling are trivially abusable. Must be implemented before any endpoint is publicly reachable.
2. **No input sanitization for user-supplied query parameters** (Grok; affirmed by GPT-4o's validation spec gap) — The `search` parameter queries PostgreSQL with ILIKE. Without sanitization, wildcard abuse and query amplification are possible. Parameterized queries must be enforced.
3. **No security headers specified for Next.js frontend** (Grok) — Content-Security-Policy, X-Frame-Options, and X-Content-Type-Options must be configured. These are table stakes for a public web frontend.
4. **Redirect type unspecified** (both models) — Using 302 instead of 301 for permanent route migrations can create open redirect abuse potential in some configurations and will harm SEO.
5. **`.gitignore` asset exclusion** (both models) — Indirect security risk: if required fallback assets cannot be committed, developers may work around the restriction by placing unversioned files in production, creating deployment inconsistency and potential supply-chain gaps.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by both models that separate a functional implementation from a truly world-class product:

1. **Comprehensive testing strategy** (both models): A migration of 1,704 records with a full rendering-stack replacement requires unit tests on all model methods, integration tests on all API endpoints, and E2E tests covering the critical user flows (listing → filter → click → detail page). Without this, the migration is a manual QA bottleneck on every deploy.

2. **On-demand ISR revalidation mechanism** (both models, different framing): Both models flagged that a fixed 60-second revalidation window is insufficient for time-sensitive content. A world-class implementation includes a webhook or admin-triggered revalidation endpoint that allows editorial teams to push updates immediately without waiting for the TTL to expire.

3. **Operational error handling and fallback UI** (both models): The spec is silent on what the Next.js frontend renders when the Flask API is unreachable. A world-class product defines error states, skeleton loaders, and graceful degradation for every user-facing page that depends on a backend call.

4. **Slug migration collision handling with audit log** (both models): A world-class migration script produces a complete audit log of every slug generated, every collision resolved, and every record transformed — so the migration can be replayed, rolled back, or verified independently.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0** | Implement the entire feature: API routes, Article model, migrations, Next.js pages, redirect logic, static assets | Entire feature directory | all (2/2) | Nothing exists. Zero shippable code. |
| **P0** | Fix `.gitignore` to allow required fallback cover images | `.gitignore:15–16` | all (2/2) | Required assets permanently blocked from version control |
| **P0** | Resolve pagination contradiction: choose page-number OR cursor — not both | `ARTICLE_PAGE_LAWS.md:136–143`, `150–157`, `172–175` | all (2/2) | Contradictory spec will produce incompatible API implementations |
| **P0** | Resolve fallback image algorithm: choose `article_id % 10` OR `hash(slug) % 10` — not both | `ARTICLE_PAGE_LAWS.md:109`, `389–390` | all (2/2) | Inconsistent images across creation paths |
| **P0** | Resolve search endpoint contradiction: one canonical search path | `ARTICLE_PAGE_LAWS.md:114`, `154`, `229` | gpt4o + affirmed by grok | Violates Law 2's "One API, One Schema" principle |
| **P0** | Add rate limiting to all public API endpoints | `ARTICLE_PAGE_LAWS.md:223–235` | all (2/2) | Public unauthenticated endpoints with no throttling are production-unsafe |
| **P0** | Add input sanitization requirements for all user-supplied query params | `ARTICLE_PAGE_LAWS.md:150–157`, `256` | all (2/2) | PostgreSQL ILIKE search without sanitization enables query amplification abuse |
| **P1** | Clarify Law 1 vs Banned Practice #2: single fallback ≠ fallback chain | `ARTICLE_PAGE_LAWS.md:109`, `447` | gpt4o | Textual contradiction will cause implementers to remove required fallback |
| **P1** | Provide separate JSON schema examples for list vs detail responses | `ARTICLE_PAGE_LAWS.md:116–147`, `158`, `253–255` | gpt4o | Single conflated example causes over-fetching bugs |
| **P1** | Clarify whether API returns absolute HTTPS or relative path for cover_image_url | `ARTICLE_PAGE_LAWS.md:109`, `202` | gpt4o | Law 10 requires HTTPS URL; Law 1 fallback is relative path — ambiguous serialization contract |
| **P1** | Add security headers requirement for Next.js deployment (CSP, X-Frame-Options, X-Content-Type-Options) | `ARTICLE_PAGE_LAWS.md` (new section) | grok | Mandatory for any public-facing web frontend |
| **P1** | Define redirect type (301 permanent) for legacy route migration | `ARTICLE_PAGE_LAWS.md:162`, `356–357` | all (2/2) | SEO preservation and canonicalization require explicit 301; unspecified = likely wrong default |
| **P1** | Define slug collision resolution algorithm for migration of existing 1,704 records | `ARTICLE_PAGE_LAWS.md:166`, `387` | all (2/2) | Collisions are probable at scale; undefined behavior = data corruption risk |
| **P1** | Add testing strategy: unit, integration, E2E requirements | `ARTICLE_PAGE_LAWS.md:416–438` | all (2/2) | Complex migration with no test requirements is unacceptable for production |
| **P2** | Define on-demand ISR revalidation escape hatch for urgent content updates | `ARTICLE_PAGE_LAWS.md:170` | grok + affirmed by gpt4o | 60-second TTL insufficient for time-sensitive editorial content |
| **P2** | Document error states and fallback UI for API unavailability | `ARTICLE_PAGE_LAWS.md:268–301` | grok | Missing from frontend spec; required for production resilience |
| **P2** | Add migration audit log requirement to execution plan | `ARTICLE_PAGE_LAWS.md:416–438` | both (inferred) | World-class migration produces a verifiable, replayable record |
| **P2** | Clarify ISR 60-second rationale and document design decision record | `ARTICLE_PAGE_LAWS.md:170` | grok | Architecture decisions should be documented with reasoning |

---

## CYCLE 2 VERDICT

**Production-ready: NO.**

This is not a close call. After two full cycles of multi-model review, the unanimous verdict is that `p4-article-page` is a planning document, not a software feature. The absolute final blockers are:

1. **Zero code exists.** There is nothing to ship. Every finding is about a spec that has not been implemented.
2. **The spec itself contains four unresolved internal contradictions** that will produce incompatible implementations if handed to any developer today (pagination model, image fallback algorithm, search endpoint, Law 1 vs Banned Practice #2).
3. **The `.gitignore` actively prevents comm

---

# WINNER DETERMINATION

# WINNER: GPT-4o

GPT-4o delivered the highest-quality analysis across both cycles by identifying the most precise, line-cited contradictions in the spec (pagination design conflict, fallback image algorithm mismatch, database coupling) before any consensus existed, and then used Cycle 2 to honestly calibrate — agreeing, disagreeing, and partially agreeing with specific evidence rather than restating prior findings. Its recommendations were the most actionable and directly traceable to specific law line numbers, making them immediately implementable by a developer.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered list — implement in this sequence. No item should be started until all items above it are unblocked.

---

## P0 — ABSOLUTE BLOCKERS (nothing else matters until these are done)

### P0-1 — Fix `.gitignore` Before Any Asset Work Begins
**Why first:** Every subsequent step that touches static files will silently fail if this is not resolved first. A developer will commit, push, and not notice the assets are missing until production.
**Action:** Remove or scope the `*.png` and `*.jpg` glob rules. Replace with path-specific ignores if needed (e.g., `/tmp/*.jpg`). Commit the 10 required fallback cover images (`btc-0.jpg` through `btc-9.jpg`) to `/static/images/default-covers/` in the same PR.

### P0-2 — Resolve the Pagination Contradiction in the Spec Before Writing Any API Code
**Why second:** If a developer reads the spec and starts building, they will build either cursor-based or page-number pagination. The other developer will build the opposite. The frontend and backend will be incompatible on day one.
**Action:** Strike Law 6's claim that "pagination is cursor-based in the API" (`ARTICLE_PAGE_LAWS.md:172–175`). The actual schema at lines 136–143 and 150–157 is unambiguously page-number based (`page`, `per_page`, `total_pages`, `has_next`, `has_prev`). Canonicalize on page-number pagination throughout the entire document. If cursor-based is genuinely desired, rewrite the schema section to match — but pick one.

### P0-3 — Resolve the Fallback Image Algorithm Contradiction
**Why third:** Two different algorithms for fallback image selection will produce different images depending on which part of the codebase is doing the selection. This creates a visually inconsistent product and an untestable contract.
**Action:** Choose exactly one algorithm and strike the other. Recommended canonical form: `btc-{article_id % 10}.jpg` (line 108–110) because `article_id` is a stable database integer. Remove the `hash(slug) % 10` variant from the factory example at lines 389–390. Add a single-line note in the spec: "All fallback image resolution MUST use article_id. slug-based hashing is forbidden."

---

## P1 — CORE BACKEND IMPLEMENTATION (implement in this order)

### P1-1 — Database Migration and Model Definition
**Action:** Write and run the PostgreSQL migration. Define the Article model with all fields specified in the laws. Include indexes on `slug` (unique), `category`, `published_at`, and `is_published`. Do not use SQLite at any stage — the spec's ILIKE search operator (`line 257`) is PostgreSQL-specific and will not work on SQLite.

### P1-2 — `/api/v2/articles` Listing Endpoint
**Action:** Implement GET with query parameters: `page` (int, default 1), `per_page` (int, default 20, max 100), `category` (string, optional), `sort` (enum: `newest`/`oldest`/`popular`), `search` (string, optional, ILIKE). Return the paginated envelope defined at lines 136–143. Add strict input validation — reject non-integer `page`, reject `per_page` above 100, reject unknown `sort` values with 400 not 500.

### P1-3 — `/api/v2/articles/{slug}` Detail Endpoint
**Action:** Implement GET by slug. Return 404 with a structured JSON error body (not an HTML error page) when slug does not exist. Return 410 Gone for deprecated slugs if redirect mapping exists. Never return a bare 500.

### P1-4 — `/api/v2/articles/categories` Endpoint
**Action:** Implement GET returning the distinct category list. This is required by the frontend filter UI and is a hard dependency for P2-2.

### P1-5 — Rate Limiting on All Public Endpoints
**Action:** Apply rate limiting to all three endpoints above. These are unauthenticated public read endpoints exposed to meaningful traffic. Implement at the Flask layer or reverse proxy. Suggested limit: 60 requests/minute per IP on listing, 120/minute on detail. Return 429 with `Retry-After` header.

---

## P2 — CORE FRONTEND IMPLEMENTATION (requires P1 complete)

### P2-1 — Article Listing Page with ISR
**Action:** Implement `/articles` as a Next.js page using ISR with 60-second revalidation. Render paginated article cards. Handle the API-down state explicitly — show a static fallback or cached content, never a blank page or unhandled exception.

### P2-2 — Category Filter UI
**Action:** Wire the category filter to `/api/v2/articles/categories`. Do not hardcode category values in the frontend. Changing a category in the database must be reflected in the UI without a code deploy.

### P2-3 — Article Detail Page with SSR and SEO Metadata
**Action:** Implement `/articles/[slug]` as a Next.js SSR page. Inject `<title>`, `<meta name="description">`, Open Graph tags, and canonical URL into `<head>` per the law requirements. Handle slug-not-found as a proper Next.js 404 page, not a JS error boundary.

### P2-4 — Fallback Image Component
**Action:** Implement the cover image component using the now-canonical `article_id % 10` algorithm from P0-3. The component must never make a network request for a missing image — it must resolve the fallback path deterministically at render time.

---

## P3 — MIGRATION AND REDIRECT INFRASTRUCTURE

### P3-1 — Legacy URL Redirect Mapping
**Action:** Implement redirect logic for any legacy article URLs to the new `/articles/{slug}` format. Use HTTP 301 (permanent) not 302. Log unmapped legacy hits so broken links can be discovered post-launch.

### P3-2 — Deprecation of `/api/v1/articles` (if it exists)
**Action:** If a v1 articles endpoint exists in the codebase, add a deprecation header (`Deprecation: true`, `Sunset: {date}`) to all v1 responses. Do not delete v1 until all known consumers have migrated. Set a hard sunset date and enforce it.

---

## P4 — TESTING AND OBSERVABILITY (required before merge to main)

### P4-1 — API Contract Tests
**Action:** Write tests covering: correct pagination envelope shape, 404 on missing slug, 400 on invalid query params, 429 on rate limit breach, fallback image path correctness for `article_id % 10` across all 10 buckets.

### P4-2 — Frontend Render Tests
**Action:** Test that SEO metadata is present in SSR output (not just client-side). Test that the fallback image renders when no cover URL is present. Test that the category filter correctly filters results.

### P4-3 — Load and Concurrency Baseline
**Action:** Run a basic load test against the listing endpoint at the documented peak concurrency (~1000 concurrent users). Establish a response time baseline before launch. If P99 exceeds 2 seconds under load, add a caching layer (Redis or CDN) before shipping.

---

## P5 — SPEC CLEANUP (do after implementation, before closing the PR)

### P5-1 — Canonicalize the Laws Document
**Action:** After implementation is complete and all contradictions are resolved, update `ARTICLE_PAGE_LAWS.md` to reflect exactly what was built. Remove all contradictory passages identified in P0-2 and P0-3. The document should be a reliable reference for future developers, not a source of ambiguity.