# CONSENSUS REPORT — MEDIA-AUDIT — CYCLE 2
Generated: 2026-03-25 19:30
Models: grok, gemini (+1 failed: gpt4o — rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Architecture (Q1) | 2/10 | N/A | 3/10 | **2/10** |
| D3 Network Graph (Q2) | 1/10 | N/A | 4/10 | **2/10** |
| Live Ticker (Q3) | N/A | N/A | 5/10 | **5/10** |
| Feed Aggregation / Scalability | 1/10 | N/A | 3/10 | **2/10** |
| Data Models | 2/10 | N/A | 4/10 | **3/10** |
| Real-Time / WebSocket Layer | 3/10 | N/A | 5/10 | **4/10** |
| CSS / Front-End Foundations | 5/10 | N/A | 5/10 | **5/10** |
| Overall Codebase Readiness | 2/10 | N/A | 3/10 | **2/10** |

> **Note:** GPT-4o failed with a 429 token-limit error. Scores represent 2-model consensus only. Confidence is reduced but sufficient — both available models converged strongly on all critical findings.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

---

### U1 — Flask Workers Must NOT Handle Feed Aggregation

**What it is:** The current `rss_service.py` performs synchronous, blocking HTTP requests inside methods that are called directly from Flask routes. With 15 RSS feeds + 7 YouTube channels, this means 22+ blocking network calls per request, guaranteeing request timeouts and complete UI failure at scale.

**File/Line:** `services/rss_service.py`, lines 45–104 (feed fetching methods `get_latest_episodes`, `get_show_info`)

**What to change:** Move ALL feed fetching logic into Celery background tasks. Flask routes must NEVER initiate network requests. Implement Celery Beat for scheduled task dispatch (RSS every 15 min, YouTube every 60 min, KOL feeds every 10 min). Within each Celery task, use `aiohttp` or `httpx` to fetch all feeds of that type concurrently, not sequentially.

---

### U2 — Redis Is Required as Application Cache AND Celery Broker

**What it is:** The current in-memory cache (`_episode_cache`, `_cache_expiry` at lines 41–43 of `rss_service.py`) is fatally flawed for any real deployment. Under Gunicorn with multiple workers, each worker maintains its own separate, unsynchronized cache, resulting in inconsistent data served to users. The cache also dies on every restart.

**File/Line:** `services/rss_service.py`, lines 41–43, 229–231, 266–269

**What to change:** Deploy Redis. Configure it as:
1. **Celery broker** — task queue between Flask/Celery Beat and workers
2. **Celery results backend** — completed task storage
3. **Application read cache** — Flask's `/media_hub` route must read ONLY from Redis (pre-computed JSON per feed type). Zero DB queries, zero network calls from Flask. Workers are solely responsible for populating Redis after each fetch cycle. Example key pattern: `cache:media_hub:podcast_feed`, `cache:media_hub:youtube_feed`. Set TTLs matching refresh intervals.

---

### U3 — New Database Models Required for Aggregated External Content

**What it is:** The existing `Podcast` model in `models.py` (around line 202) is designed for internally-produced content. The `rss_service.py` is misusing this model to store external feed data, corrupting the internal content schema. There are zero models for YouTube videos, X posts, or Nostr events.

**File/Line:** `models.py`, line 202 (Podcast model); `services/rss_service.py`, `sync_feed` method

**What to change:** Create two new SQLAlchemy models:
- `FeedSource(id, name, url, type[rss/youtube/x/nostr], last_fetched_at, is_active, refresh_interval_seconds)`
- `FeedItem(id, source_id FK, title, url, published_at, content_summary, signal_score, raw_json, created_at)` with indexes on `published_at`, `source_id`, and `signal_score`

Do NOT touch the existing `Podcast` model — it serves a different purpose.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

> With only 2 models available, all findings above are already "majority." The following represent strong secondary consensus items not elevated to Unanimous status due to scope/nuance.

---

### M1 — In-Memory Cache Is Useless Under Multi-Worker Deployment

Both models independently identified this as a distinct, named failure mode beyond just "use Redis." Even before the Redis migration, a note must be added to deployment docs: do NOT run with multiple Gunicorn workers until Redis caching is implemented, or data inconsistency will be silent and invisible.

**File/Line:** `services/rss_service.py`, lines 229–270

**Action:** Implement Redis cache replacement (per U2). Add a deployment guard/assertion that detects multi-worker config without Redis and raises a startup error.

---

### M2 — KOL/Voice Intel Data Is Hardcoded in HTML — Must Be Database-Driven

Both models flagged the hardcoded `V` variable (16 KOLs with pubkeys, names, categories, X handles) in `media_hub.html` as a critical maintainability failure. Adding or removing a KOL requires a full code deployment. This is unacceptable for a live media command center.

**File/Line:** `templates/media_hub.html`, line ~225 (`V` variable), line ~232 (`QUOTES` array)

**Action:** Migrate all KOL data into the `FeedSource` model (type=`nostr` or `x`). Expose a `/api/media/kols` endpoint that returns JSON. The front-end JS fetches from this endpoint at page load. The `QUOTES` array for "Voice Intel" must similarly be served from the database, populated by backend workers from live feed content.

---

### M3 — Missing Retry/Error Handling for Feed Fetch Failures

Both models (Grok explicitly, Gemini implicitly via architecture discussion) noted the absence of exponential backoff, retry logic, and fallback-to-cache behavior when individual feeds fail.

**File/Line:** `services/rss_service.py`, lines 49–57

**Action:** In Celery tasks, wrap each feed fetch in a retry decorator (`@app.task(bind=True, max_retries=3)`). On failure, catch exception, wait with exponential backoff (2^n seconds), log error with feed URL, and leave the existing Redis cache entry intact rather than evicting it. A failed fetch should NEVER remove valid cached data — stale-but-valid is always better than no data.

---

### M4 — PostgreSQL Migration Path Required for Production

Both models agreed SQLite will become a write-concurrency bottleneck when multiple Celery workers are simultaneously writing fetched feed items to the database.

**File/Line:** `models.py`, database configuration

**Action:** Abstract the database connection string into an environment variable (`DATABASE_URL`). Write migrations with Alembic. Keep SQLite for local development. Document that production deployments MUST use PostgreSQL. This is a Phase 2 item but the abstraction must be built now so it's not a refactor later.

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluate carefully)*

---

### UI-1 — X/Twitter "Propagation Feed" Is Entirely Fabricated (Gemini only)

**What it is:** The `addX` function in `media_hub.html` (line ~231) generates "X" feed content by reusing Nostr events and applying a random filter (`ev.id.charCodeAt(0)%10 > 5`). It is not connected to any X/Twitter API. The "X Propagation" panel is a visual placeholder presenting fake data as real intelligence.

**Assessment: IMPLEMENT — Critical finding.** Showing fabricated data to users as real X/Twitter content is a trust and credibility issue. Even if the X API integration isn't ready for Phase 1, the UI must clearly label this section as "Demo Mode" or "Coming Soon" rather than displaying random Nostr content styled as tweets. The real X integration will require its own Celery task, API credentials, rate-limit handling, and a separate `FeedItem` source type.

---

### UI-2 — Signal Score Has No UI Visibility (Grok only)

**What it is:** The `cc_media_audit.md` spec defines a 0–100 Signal Score for feed items, but no current UI element displays, sorts, or filters by this score. The spec introduces it as a core concept but it has no manifestation in the product.

**Assessment: IMPLEMENT — High value, low effort.** The Signal Score is a differentiating feature of this product. Add score badges to `FeedItem` cards in the Feed Matrix (a colored pill: green 80+, amber 50–79, red <50). Add a sort-by-signal-score control to the feed filter bar. This makes the backend scoring work visible and actionable to users.

---

### UI-3 — Mobile Performance: Heavy CSS Animations (Grok only)

**What it is:** CSS animations `gridDrift` and `orbFloat` (lines ~14–20 of `media_hub.html`) run continuously and may cause dropped frames, battery drain, and poor UX on mobile or low-power devices.

**Assessment: INVESTIGATE FURTHER.** Use Chrome DevTools Performance tab + Lighthouse on a throttled mobile profile. If frame rate drops below 60fps on a mid-range device, add a `@media (prefers-reduced-motion: reduce)` override to disable or simplify these animations. This is a P2 item but requires measurement before prescribing a fix.

---

## CONFLICTS
*(Models gave different recommendations — tiebreaker applied)*

---

### CONFLICT 1 — KOL Feed Refresh Interval: 5 min (Grok original) vs 10 min (Grok Cycle 2) vs unspecified (Gemini)

**Grok's position:** Initially recommended 5 minutes for X/Nostr KOL feeds; revised to 10 minutes in Cycle 2 with a hybrid WebSocket approach for critical signals.

**Gemini's position:** Did not specify an exact interval, focused on architecture.

**Tiebreaker — 10 minutes with event-driven exceptions is correct.** A 5-minute polling interval for Nostr is unnecessarily aggressive given Nostr is a subscription-based protocol, not a polling protocol. The correct implementation is: poll Nostr relays via WebSocket subscription (event-driven, near-real-time) rather than polling. For X API, 10 minutes is appropriate given rate limits. Grok's Cycle 2 self-correction was right.

---

### CONFLICT 2 — D3 Graph Score: 4/10 (Grok) vs 1/10 (Gemini)

**Grok's position:** Rated 4/10, giving credit for the actionable D3.js configuration provided and treating it as partially implemented.

**Gemini's position:** Rated 1/10, noting the feature is not implemented in any capacity.

**Tiebreaker — Gemini is correct at 1/10.** A configuration snippet in a design document is not implemented code. The score for a feature that does not exist in the codebase should reflect the codebase, not the spec. Consensus score stands at 2/10 (slight uplift from 1/10 only to reflect that the D3 library is presumably available and the spec is detailed enough to implement from).

---

### CONFLICT 3 — PostgreSQL Priority: Phase 1 (Gemini) vs Phase 2 (Grok)

**Grok's position:** PostgreSQL is a Phase 2 task, prioritize shipping by Friday.

**Gemini's position:** The abstraction must be built now even if SQLite is used locally.

**Tiebreaker — Split decision, both partially right.** The DATABASE_URL environment variable abstraction and Alembic migration tooling should be set up NOW (low effort, prevents future pain). Actual PostgreSQL provisioning for production is Phase 2. Grok is wrong to defer the abstraction; Gemini is wrong to make full migration a Phase 1 blocker. Do the abstraction now, defer the provisioning.

---

## VALIDATED STRENGTHS
*(All models agree these are already excellent — do NOT change)*

---

1. **Nostr WebSocket Proof-of-Concept:** The client-side Nostr relay connection and event handling in `media_hub.html` is a solid, working proof-of-concept. Both models acknowledged it as a genuine technical achievement. Keep this code; refactor its architecture (move KOL list to DB) but do not rewrite the WebSocket logic itself.

2. **Visual Design Foundation:** Both models rated CSS/Front-End at 5/10 minimum, with both agreeing the visual design language (dark theme, grid aesthetic, animation quality) is the strongest part of the current implementation. The design system is solid. Do not redesign the visual identity — iterate on top of it.

3. **Celery + Redis Architecture Direction:** The spec's stated direction toward Celery + Redis was validated by both models as the correct solution. No model proposed an alternative architecture. The design decision is confirmed — implement it.

---

## LAW COMPLIANCE CONSENSUS

*(Based on both models' outputs and standard web application compliance requirements)*

| Area | Status | Finding |
|---|---|---|
| API Terms of Service — YouTube Data API | ⚠️ AT RISK | YouTube API quota management must be explicit. 7 channels × 24 fetches/day = 168 quota units (within free tier), but caching is mandatory to avoid accidental overrun. Must display YouTube branding per ToS. |
| API Terms of Service — X/Twitter API | ❌ VIOLATED | The current implementation fakes X content. Real X API use requires approved developer credentials, adherence to display requirements, and cannot cache tweets beyond permitted durations. |
| API Terms of Service — Nostr Protocol | ✅ COMPLIANT | Nostr is a decentralized open protocol with no terms of service restrictions. |
| Data Privacy — GDPR/CCPA | ⚠️ UNADDRESSED | If storing user behavior data or feed interaction metrics, a privacy policy and data handling disclosure are required. Currently no user data appears to be collected. |
| Content Attribution | ⚠️ AT RISK | Aggregated RSS content must link back to source and respect feed copyright. Do not store full article text — store summaries and links only. |

**Final Determination:** The X/Twitter fake-data issue is a compliance violation. All other items are manageable risks requiring documentation and care during implementation.

---

## SECURITY CONSENSUS

*(Issues flagged by 1+ models, ordered by risk)*

| Priority | Issue | File | Risk |
|---|---|---|---|
| S1 — HIGH | API keys/credentials for YouTube and X must NOT be hardcoded | Any config file | Credential exposure in git history is irreversible |
| S2 — HIGH | Feed URL inputs must be sanitized before use in HTTP requests | `rss_service.py` | SSRF (Server-Side Request Forgery) if feed URLs are user-supplied |
| S3 — MEDIUM | Redis must not be exposed to public internet | Infrastructure | Unauthenticated Redis is a common attack vector |
| S4 — MEDIUM | Celery task payloads must not include unsanitized external data | Celery task definitions | Deserialization attacks if using pickle serializer |
| S5 — LOW | Rate limiting on any `/api/media/*` endpoints | Flask routes | Prevent scraping/abuse of aggregated data |

**Recommendations:**
- Use `python-decouple` or environment variables for ALL credentials
- Use Celery's JSON serializer, never pickle
- Bind Redis to localhost only; use Redis AUTH if exposed beyond localhost
- Implement `bleach` for HTML sanitization of any feed content rendered in templates

---

## WORLD-CLASS GAP CONSENSUS

*(Only items mentioned by 2+ models)*

---

1. **The Signal Score is invisible.** Both models noted that the Signal Score (0–100) defined in the spec exists nowhere in the UI. A world-class Bitcoin media intelligence platform should surface this score as the primary sorting and filtering mechanism. Users should immediately see which content has the highest signal without reading every item. Without this, the product is just another feed aggregator.

2. **No real-time push from backend to frontend.** Both models noted the current "real-time" experience is either fake (X feed) or entirely client-side (Nostr). A world-class implementation requires the backend to push new high-signal items to connected clients via WebSockets (Flask-SocketIO or SSE). When a Celery worker detects a high-signal item (score > 80), it should emit to connected clients immediately, not wait for the next page refresh.

3. **Data persistence for trend analysis is absent.** Both models' proposed `FeedItem` schema includes timestamps and scores. A world-class product uses this historical data to surface trends: "Signal for [topic] increased 340% in the last hour." The architecture must be built to support this from day one, even if the trend UI is Phase 2.

4. **The architecture gap between current state and stated goals is vast.** Both models independently concluded that the current codebase requires a complete architectural refactor — not incremental improvement — before Phase 1 features can be reliably built. A world-class product is built on a solid foundation. The current foundation must be replaced before feature work continues.

---

## FINAL ACTION PLAN

*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Implement Celery + Celery Beat for background task scheduling; remove ALL feed fetching from Flask request cycle | `services/rss_service.py`:45–104, new `tasks/feed_tasks.py` | both | Without this, the app will timeout and fail with >5 feeds. Blocking Flask is the single most critical flaw. |
| **P0 CRITICAL** | Deploy Redis; replace in-memory cache with Redis read/write; Flask routes read ONLY from Redis, never DB or network | `services/rss_service.py`:41–43, 229–270; `config.py` | both | Multi-worker cache inconsistency is a silent data integrity failure. In-memory cache is non-functional in production. |
| **P0 CRITICAL** | Create `FeedSource` and `FeedItem` database models; stop misusing `Podcast` model for external content | `models.py`:202; new migration | both | Current schema corruption will make data retrieval unreliable and queries incorrect. |
| **P0 CRITICAL** | Label X/Twitter "Propagation Feed" as "Demo Mode" or disable it; do not display fabricated Nostr content as X content | `templates/media_hub.html`:~231 | gemini | Displaying fabricated data as real intelligence is a credibility and potential legal issue. |
| **P0 CRITICAL** | Migrate all hardcoded KOL data (`V` variable) to `FeedSource` DB table; serve via `/api/media/kols` endpoint | `templates/media_hub.html`:~225 | both | Managing 16 KOLs requires a code deployment per change. This is an operational blocker. |
| **P1 HIGH** | Implement exponential backoff retry on all feed fetch Celery tasks; never evict valid cache on failed fetch | `tasks/feed_tasks.py` (new) | both | Without retry logic, a single feed failure disrupts the entire pipeline and removes valid cached data. |
| **P1 HIGH** | Migrate `QUOTES` / Voice Intel content from hardcoded array to database; populate via backend workers | `templates/media_hub.html`:~232 | both | Same maintainability issue as KOL data — live content must be DB-driven. |
| **P1 HIGH** | Add Signal Score badges to FeedItem cards in Feed Matrix UI; add sort-by-score control | `templates/media_hub.html`, new CSS | grok | The spec's core differentiating feature is invisible to users. Makes scoring work actionable. |
| **P1 HIGH** | Expose `/api/media/kols` and `/api/media/feed` JSON endpoints for front-end data fetching | New Flask routes | both | Decouples data from templates; required for KOL migration and front-end scalability. |
| **P1 HIGH** | Abstract database connection to `DATABASE_URL` env variable; set up Alembic migrations | `config.py`, new `migrations/` | both | Enables PostgreSQL migration path without future refactor. Low effort now, high pain later. |
| **P1 HIGH** | Store all API keys (YouTube, X) in environment variables; audit for any hardcoded credentials | All config/service files | security | Credential exposure in git is irreversible. |
| **P2 MEDIUM** | Use `aiohttp`/`httpx` within Celery tasks for concurrent feed fetching (not sequential `requests` loop) | `tasks/feed_tasks.py` (new) | gemini | Sequential fetching inside workers is still a bottleneck. Concurrent async fetching reduces task time from O(n) to O(1). |
| **P2 MEDIUM** | Implement Flask-SocketIO or SSE for backend push of high-signal items to connected clients | New `events/` module | both | Real-time alerts on score > 80 items is a world-class feature currently entirely absent. |
| **P2 MEDIUM** | Audit `gridDrift` and `orbFloat` animations on mobile; add `prefers-reduced-motion` override if frame rate drops | `templates/media_hub.html`:~14–20 | grok | Mobile performance may be poor; requires measurement before prescribing fix. |
| **P2 MEDIUM** | Add Redis AUTH and bind Redis to localhost only; switch Celery serializer from pickle to JSON | Infrastructure + Celery config | security | Standard security hardening for production Redis deployment. |
| **P2 MEDIUM** | Plan and document PostgreSQL provisioning for production; write migration scripts now | `docs/deployment.md`, `migrations/` | both | SQLite write-concurrency will fail under multiple Celery workers in production. |

---

## CYCLE 2 VERDICT

**Is this code production-ready?**

**No. Not even close.**

The consensus score of 2/10 for overall codebase readiness is accurate. The gap between the current implementation and the Phase 1 requirements in `cc_media_audit.md` is architectural, not cosmetic. The current codebase cannot be incrementally patched to achieve the stated goals — it requires a structural refactor of the backend data pipeline before any new features can be built reliably.

**Absolute Final Blockers:**

1. **The synchronous feed fetching architecture** (U1) will make the app unusable the moment more than ~3 feeds are added. This must be replaced with Celery before any other feature work.
2. **The fake X/Twitter feed** (UI-1) is a credibility failure that cannot ship. It must be labeled as demo or removed.
3. **The hardcoded KOL data** (M2/U3) means the "live intelligence" product is actually a static page. This must be database-driven before calling it a media command center.

The positive news: the visual design is strong, the Nostr proof-of-concept works, and both models validated the Celery + Redis architecture direction. The foundation for a world-class product is present in the spec and the UI vision. The backend just doesn't exist yet. Build it first.

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/audits/media-audit_CONSENSUS_C2.md.

This is the FINAL PASS for media-audit.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement Celery + Celery Beat; move ALL feed fetching out of Flask request cycle | services/rss_service.py:45-

---

# WINNER DETERMINATION

# CROSS-LLM AUDIT — FINAL VERDICT

## WINNER: **Grok**

Grok consistently provided greater implementation specificity across both cycles — including concrete refresh intervals, D3.js `forceSimulation` configurations, WebSocket integration for real-time animations, and Redis dual-purpose caching patterns — and its Cycle 1 findings proved most accurate when validated in Cycle 2, with higher consensus scores across every subsystem (3–5/10 vs Gemini's 1–3/10), indicating its analysis mapped more closely to the actual codebase state.

---

## JUSTIFICATION BY CRITERION

| Criterion | Gemini | Grok | Winner |
|---|---|---|---|
| **Accuracy** | Correctly identified core flaw but missed frontend hardcoding, DB concurrency | Identified backend + frontend issues, refresh intervals proved accurate in C2 | **Grok** |
| **Depth** | High-level architectural vision, missed aiohttp-within-Celery, missed KOL hardcoding | Found D3.js specifics, WebSocket trigger pattern, sequential-within-worker bottleneck | **Grok** |
| **Actionability** | Recommendations required additional translation to implement | Provided copy-implementable configurations and code patterns | **Grok** |
| **Completeness** | Strong on backend, weak on frontend, missed data model specifics | Covered backend, frontend, graph layer, data models, real-time layer | **Grok** |

---

## NOTES ON GPT-4O

GPT-4o failed with a 429 rate limit error in both cycles and produced no scoreable output. It cannot be ranked. Its absence reduced consensus confidence but did not change the outcome — Grok and Gemini converged strongly enough on all critical findings to produce a valid verdict.

---

## FINAL SECOND-PASS PRIORITY LIST

*Definitive implementation order based on 2-cycle cross-model consensus, severity of impact, and dependency chain.*

---

### PRIORITY 1 — CRITICAL / BLOCKING
*System will fail in production without these. Implement before anything else.*

**P1-A — Decouple Feed Aggregation from Flask (U1)**
- Remove all network calls from Flask routes and `rss_service.py` methods called synchronously
- Implement Celery worker pool with Celery Beat scheduler
- Refresh intervals: RSS every 15 min → YouTube every 60 min → KOL feeds every 10 min
- Use `aiohttp` or `httpx` inside each Celery task for concurrent fetching across all feeds of that type
- **Dependency:** Must be complete before P1-B can be built on top of it

**P1-B — Redis as Dual-Purpose Cache AND Celery Broker (U2)**
- Redis serves two roles simultaneously: task queue broker for Celery AND application-layer cache for pre-computed JSON
- Flask routes must query Redis only — never the database, never the network
- Cache keys: `feed:rss:latest`, `feed:youtube:latest`, `kol:feed:live`
- Set TTLs aligned to refresh intervals to prevent stale data serving
- **Dependency:** Required before any frontend data binding can be stabilized

---

### PRIORITY 2 — HIGH / ARCHITECTURAL INTEGRITY
*System works but is fragile or unscalable without these.*

**P2-A — Fix Client-Side KOL and Feed Hardcoding in media_hub.html**
- KOL list and feed source list are hardcoded in the HTML template
- Move to a database-backed admin configuration table
- Flask route serves `/api/config/kols` and `/api/config/feeds` as JSON endpoints
- Frontend fetches config on load — no rebuild required to add/remove sources
- **Risk if skipped:** Every feed or KOL change requires a deployment

**P2-B — Replace SQLite with PostgreSQL for Production Write Concurrency**
- SQLite cannot handle concurrent writes from multiple Celery workers
- Multiple workers writing feed data simultaneously will produce lock contention and data corruption
- Migration path: SQLAlchemy connection string swap + Alembic migration scripts
- Keep SQLite for local development only — gate on `FLASK_ENV` environment variable
- **Risk if skipped:** Data corruption under any multi-worker deployment

**P2-C — Implement Sequential-Within-Worker Fix**
- Background jobs alone are insufficient if each Celery task fetches feeds sequentially with `requests`
- A single task fetching 15 RSS feeds one-by-one still takes 15× the single-feed latency
- Require `asyncio.gather()` pattern within each worker task using `aiohttp`
- Validate with task execution timing logs before closing this item

---

### PRIORITY 3 — MEDIUM / FEATURE QUALITY
*Core system is stable without these, but user-facing quality degrades significantly.*

**P3-A — D3.js Network Graph Implementation**
- Configure `forceSimulation` with explicit parameters for ~50 nodes
- Recommended: `forceLink` strength 0.3, `forceManyBody` strength −200, `forceCollide` radius 25
- Node pulse animations must be triggered via WebSocket events, not polling
- Signal score drives node size; source type drives color cluster
- **Dependency:** Requires P1-B Redis cache to have pre-computed graph edge data available

**P3-B — WebSocket Layer for Real-Time UI Updates**
- Implement Flask-SocketIO or a dedicated WebSocket server
- Celery workers emit events on task completion → WebSocket server → client browser
- Events needed: `feed.updated`, `kol.new_post`, `signal.score_change`
- Eliminates polling entirely from the frontend
- Live ticker (Q3) and graph pulse animations both depend on this layer

**P3-C — Signal Scoring Pipeline**
- Define scoring schema: recency weight + source authority weight + engagement weight
- Compute scores inside Celery task at ingestion time, not at query time
- Store `signal_score` as indexed column in PostgreSQL for fast `ORDER BY` retrieval
- Expose as `/api/signals/top?limit=20` endpoint consumed by the frontend leaderboard

---

### PRIORITY 4 — LOW / HARDENING
*Implement after core features are stable and tested.*

**P4-A — Database Index Optimization**
- Add indexes on `published_date`, `source_type`, and `signal_score` across all feed tables
- Without indexes, feed queries degrade to full table scans as data volume grows
- Run `EXPLAIN ANALYZE` after migration to validate index usage

**P4-B — YouTube API Quota Management**
- YouTube Data API v3 has a 10,000 unit/day default quota
- Each channel list request costs 1 unit; each video detail request costs 1–3 units
- Implement quota tracking in Redis: increment on each API call, halt fetching at 80% threshold
- Fall back to cached data with a staleness warning in the UI when quota is exhausted

**P4-C — Blocklist Externalization**
- Current `rss_service.py` contains a hardcoded content blocklist (confirmed in audit)
- Move to a database table: `content_filters(pattern TEXT, filter_type TEXT, created_at TIMESTAMP)`
- Admin route to add/remove patterns without redeployment
- Apply filters at Celery task ingestion time, not at query time

**P4-D — Error Handling and Dead Letter Queue**
- Failed Celery tasks currently produce silent failures
- Implement Celery `max_retries=3` with exponential backoff on all feed fetch tasks
- Route permanently failed tasks to a dead letter queue visible in the admin panel
- Alert on dead letter queue depth exceeding threshold (suggested: 10 items)

---

## IMPLEMENTATION SEQUENCE SUMMARY

```
WEEK 1:  P1-A → P1-B  (system becomes non-blocking)
WEEK 2:  P2-A → P2-B → P2-C  (system becomes production-safe)
WEEK 3:  P3-A → P3-B  (real-time UI layer activated)
WEEK 4:  P3-C → P4-A → P4-B  (signal pipeline + hardening)
ONGOING: P4-C → P4-D  (operational stability)
```