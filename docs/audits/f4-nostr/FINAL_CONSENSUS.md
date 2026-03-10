# CONSENSUS REPORT — F4-NOSTR — CYCLE 2
Generated: 2026-03-09 02:43
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 1/10 | 2/10 | 1/10 | **1/10** |
| Law Compliance | 1/10 | 1/10 | 1/10 | **1/10** |
| Security | 7/10 | 6/10 | 6/10 | **6/10** |
| Frontend Quality | 4/10 | 5/10 | 5/10 | **4/10** |
| Backend Quality | 2/10 | 4/10 | 4/10 | **3/10** |
| **Overall** | **2/10** | **3/10** | **2/10** | **2/10** |

> **Synthesizer note:** The spread is narrow. All three models converged sharply downward from Cycle 1 after cross-pollination. The consensus overall is 2/10 — the feature is a non-functional shell with critical correctness bugs even in the code that was written.

---

## UNANIMOUS FINDINGS
*(all 3 models agree — implement unconditionally)*

### U1 — `nostr_monitor.py` is entirely absent
- **What:** The core monitor service — relay WebSocket connections, asyncio event loop, event deduplication, LAW 1 scoring pipeline, DB ingestion, and reconnect logic — does not exist in the submitted code.
- **File:** `nostr_monitor.py` (missing — must be created from scratch)
- **Change:** Implement the full monitor. Must include: `asyncio` event loop; 4 concurrent WebSocket connections to approved relay list; NIP-01 `REQ` subscription with `kinds: [1, 30023]` and `#t: ['bitcoin', 'btc', 'lightning', 'nostr', 'sovereignty']`; event dedup by `id` before scoring; in-memory queue with max depth 1000; flush to DB every 60s; exponential backoff on disconnect.
- **Laws violated:** LAW 2, LAW 3, LAW 4

### U2 — LAW 5 publishing is entirely absent
- **What:** No NIP-23 article publisher, no NIP-1 video publisher, no keypair management, no 10-posts/day rate limiter, no connection to Protocol Pulse content pipeline.
- **File:** Missing publishing service module
- **Change:** Implement a publishing service that reads Protocol Pulse content, constructs NIP-23/NIP-1 events, signs with managed keypair, publishes to approved relays, enforces ≤10 posts/day.
- **Law violated:** LAW 5

### U3 — LAW 1 engagement scoring computation is absent
- **What:** Schema fields (`zaps`, `quotes`, `reposts`, `replies`, `reactions`, `engagement_score`) exist in `models.py` but no code anywhere computes the score. The DB column is presumably always 0 or set externally.
- **File:** Missing — would belong in `nostr_monitor.py` ingestion pipeline
- **Change:** Implement: `score = zaps*10 + quotes*5 + reposts*3 + replies*2 + reactions*1` as part of the ingestion path. Must match LAW 1 exactly.
- **Law violated:** LAW 1

### U4 — `seed_tracked_pubkeys()` rollback bug causes silent data loss
- **What:** `db.session.rollback()` inside the per-row exception handler rolls back **all** previously staged inserts in the current session, not just the failing row. The `inserted` counter still increments, falsely reporting success.
- **File:** `core/services/nostr_service.py:112-115`
- **Change:** Either (a) validate all rows before any insert, then commit once; or (b) use per-row savepoints (`db.session.begin_nested()`); or (c) flush+commit per row and catch at individual row scope.

### U5 — Invalid seed pubkeys (63 chars, not 64)
- **What:** At least three seeded pubkeys are 63 hex characters instead of the required 64. SQLite/Postgres `String(64)` does not enforce length; bad values persist silently and will break any author-based relay filtering.
- **File:** `core/services/nostr_service.py:34, 40, 64`
- **Change:** Correct each to a valid 64-char hex pubkey or remove if no valid replacement is known. Add a validation assertion in the seed function.

### U6 — UI scoring formula is inconsistent with LAW 1
- **What:** The prose explainer at `nostr.html:500-503` lists `zaps > reposts > replies > reactions` but omits **quotes ×5**. The legend at `541-554` omits **reactions ×1**. Users are shown a materially wrong description of how content is ranked.
- **File:** `core/templates/nostr.html:500-503, 541-554`
- **Change:** Prose must read: `zaps ×10 > quotes ×5 > reposts ×3 > replies ×2 > reactions ×1`. Legend must include all five entries with correct multipliers.

---

## MAJORITY FINDINGS
*(2 of 3 models agree — implement unless compelling reason not to)*

### M1 — Relay status IPC via flat JSON file is fragile (Gemini + GPT-4o)
- **What:** `get_relay_status()` reads `state/nostr_relay_status.json` for inter-process communication. No atomic write, no file lock, no partial-read protection. If the monitor crashes mid-write, the web layer reads corrupt/stale data.
- **File:** `core/services/nostr_service.py:186-219`
- **Change:** Replace with either a dedicated DB table (`nostr_relay_status`) or write via atomic temp-file + rename. If the file approach is kept for simplicity, the writer must write to a temp file and `os.replace()` atomically.

### M2 — `<canvas>` usage for QR code violates stated stack constraint (Gemini + GPT-4o)
- **What:** `nostr.html:515, 650` uses a `<canvas>` element to render a QR code. The project has an explicit "NO Canvas" rule in the stack constraints.
- **File:** `core/templates/nostr.html:515, 650-657`
- **Change:** Replace with an SVG-based QR library or a server-rendered static image. Several pure-SVG JS QR libraries exist (e.g., `qrcode-svg`).

### M3 — Relay `last_event_at` timestamp dropped on JS refresh (GPT-4o + Grok)
- **What:** Server-side render shows `last_event_at` in the relay status panel, but the JavaScript polling refresh at `nostr.html:776-779` re-renders without that field, causing it to disappear after the first client-side update.
- **File:** `core/templates/nostr.html:776-779`
- **Change:** Ensure the API response for `/api/nostr/relay-status` includes `last_event_at` and the JS template function renders it.

### M4 — `follower_tier` sorted as string not logical rank (Gemini + GPT-4o)
- **What:** `nostr_service.py:229-232` orders by `follower_tier.desc()`, which is a lexicographic string sort (`'vip' > 'high' > 'medium' > 'low'` alphabetically, but this is coincidentally wrong for `'medium'` vs `'low'` which does sort correctly, while `'vip'` vs `'high'` is not guaranteed across all DB collations).
- **File:** `core/services/nostr_service.py:229-232`
- **Change:** Use a SQL `CASE` expression for deterministic tier ordering: `CASE WHEN follower_tier='vip' THEN 4 WHEN follower_tier='high' THEN 3 WHEN follower_tier='medium' THEN 2 ELSE 1 END DESC`.

### M5 — Feed UI does not display quotes despite quotes being part of score (GPT-4o + Grok, implicit in Gemini)
- **What:** The rendered event cards show zaps/reposts/replies/reactions counts but not quotes, even though `quotes` contributes the second-highest weight to `engagement_score`. Users cannot see a key component of the score they're looking at.
- **File:** `core/templates/nostr.html:582-593` (server render), `739-742` (JS render)
- **Change:** Add quotes count display to both the Jinja template render and the JS client refresh render, consistent with other engagement stats.

### M6 — Cron import path is fragile and may fail (GPT-4o + Grok)
- **What:** `cron/nostr_cron.py` modifies `sys.path` and imports from `services.nostr_service`. Depending on execution context (cwd, venv, cron daemon), this import may resolve incorrectly or fail silently, making scheduled pruning and stats updates unreliable.
- **File:** `cron/nostr_cron.py:77, 87`
- **Change:** Use explicit absolute import paths consistent with the project's module structure, or restructure to use a proper package entry point. Verify with a dry-run in the target cron environment.

---

## UNIQUE INSIGHTS
*(single-model catches — evaluated individually)*

### From Grok

**G1 — Error logging for relay status file failures is at `debug` level**
- `nostr_service.py:202` logs file read failures as `debug`, which won't surface in production.
- **Assessment: IMPLEMENT.** Low-effort, high-signal fix. Elevate to `WARNING`.

**G2 — No visibility API check on JS polling (unthrottled relay refresh)**
- `nostr.html:766` polls every 30s regardless of whether the tab is active.
- **Assessment: INVESTIGATE.** Low priority for launch but worth adding `document.visibilityState` check for scale. Flag as P2.

**G3 — No format validation for Nostr event IDs before storage**
- `models.py:918` stores `event_id` as `String(64)` with no hex-format validation.
- **Assessment: IMPLEMENT (P1).** Malformed IDs could cause silent downstream failures. Add a validator in the ingestion path.

### From GPT-4o

**P1 — `get_top_content()` has no secondary sort for tied scores**
- `nostr_service.py:143, 151` orders only by `engagement_score.desc()`. Ties produce non-deterministic feed ordering across paginations/refreshes.
- **Assessment: IMPLEMENT (P2).** Add `.order_by(NostrMonitorEvent.engagement_score.desc(), NostrMonitorEvent.created_at.desc())`.

**P2 — `seed_tracked_pubkeys()` unnecessarily enters `app.app_context()` inside function**
- `nostr_service.py:94` pushes a nested app context inside a function already called from an app context.
- **Assessment: INVESTIGATE.** Not a bug in typical Flask operation but signals poor boundary design. Refactor when addressing the P0 transaction bug.

**P3 — `/ads/go/{ad.id}` vs `ad.target_url` in ad injection (`app.py:178`)**
- **Assessment: SKIP for this feature.** Ad routing is not in scope for f4-nostr. Flag for a separate ad-system audit.

### From Gemini

**G4 — System-wide import fragility / no application factory pattern**
- App, service, and cron all use `sys.path` hacks and `__name__ == "__main__"` guards instead of a proper Flask application factory.
- **Assessment: INVESTIGATE (systemic).** This is a real architectural debt but out of scope for a single-feature fix pass. Flag for a dedicated refactor ticket.

**G5 — `NostrMonitorEvent.created_at` uses Unix integer while other models use `DateTime`**
- `models.py:930` stores Nostr's `created_at` as an integer (correct for Nostr protocol) but this creates inconsistency with the rest of the ORM.
- **Assessment: IMPLEMENT carefully.** The Nostr protocol natively uses Unix timestamps. Keep as integer but add a `@property` helper for human-readable conversion and document the intentional deviation.

**G6 — Frontend polling should use WebSockets rather than HTTP polling**
- 5-minute content poll + 30-second relay poll from every client will not scale.
- **Assessment: P2 / post-launch.** Valid architectural concern but not a launch blocker. Flagged in World-Class Gap section below.

---

## CONFLICTS
*(models disagree — synthesizer tiebreaker)*

### C1 — XSS risk in `nostr.html`
- **GPT-4o:** Mostly dismisses XSS concern; notes Jinja autoescaping and `escapeHtml()` in JS are adequate.
- **Grok:** Does not flag XSS independently.
- **Gemini:** Does not flag XSS.
- **Verdict: GPT-4o is correct.** Jinja2 autoescaping is on by default and the JS refresh uses `escapeHtml()`. No demonstrated XSS vector in the provided code. Do not add noise here.

### C2 — `flask_socketio async_mode="threading"` as LAW 4 evidence
- **GPT-4o:** Explicitly disagrees that this setting is evidence of LAW 4 violation — it's orthogonal to whether a separate process uses asyncio.
- **Grok:** Uses it as circumstantial evidence.
- **Verdict: GPT-4o is correct.** Flask-SocketIO's threading mode is about the web server's concurrency model, not about whether an external monitor process uses asyncio. The LAW 4 violation stands on its own merits (monitor is absent), but this specific piece of evidence is invalid.

### C3 — Severity of static engagement scores
- **Grok:** Rates this as P1 (dynamic updates needed urgently).
- **GPT-4o/Gemini:** Treat it as subsumed by the larger "no monitor = no scoring at all" issue.
- **Verdict: GPT-4o/Gemini are correct.** Once the monitor is implemented, this becomes a design question within that implementation. It is not a separate P1 bug in the existing code — it's an implementation note for the monitor.

---

## VALIDATED STRENGTHS
*(all models confirm — do NOT change in second pass)*

1. **`get_top_content()` fallback logic** — Correctly falls back from 24h recent to all-time top when no recent events exist (`nostr_service.py:148-153`). Elegant edge case handling.
2. **`cron/nostr_cron.py` prune query** — Fetches VIP pubkeys once, uses result in a single `DELETE` statement. No N+1 pattern. Well-structured.
3. **`NostrMonitorEvent` schema fields** — The model has all necessary columns (`zaps`, `quotes`, `reposts`, `replies`, `reactions`, `engagement_score`, `event_id`) with appropriate indexes. Schema foundation is correct.
4. **Loading / empty / error states in frontend** — The page handles loading spinners, empty-feed messages, and error states for the content feed and relay status (`nostr.html:560-612, 703-786`). Good UX baseline.
5. **ORM usage throughout** — SQLAlchemy ORM is used consistently, preventing raw SQL injection vectors. Security baseline is sound.

---

## LAW COMPLIANCE CONSENSUS

| Law | Description | Status | Evidence |
|---|---|---|---|
| LAW 1 | Engagement scoring formula (zaps×10, quotes×5, reposts×3, replies×2, reactions×1) | ❌ **VIOLATED** | Schema fields exist but no computation code present anywhere |
| LAW 2 | Connect to all 4 approved relays with failover + exponential backoff | ❌ **VIOLATED** | `nostr_monitor.py` missing entirely |
| LAW 3 | Bitcoin signal filter — NIP-01 subscription with specified kinds and hashtags | ❌ **VIOLATED** | `nostr_monitor.py` missing entirely |
| LAW 4 | Asyncio event loop, concurrent WebSocket connections, dedup by ID, max queue 1000, 60s flush | ❌ **VIOLATED** | `nostr_monitor.py` missing entirely |
| LAW 5 | Publish PP content to Nostr (NIP-23/NIP-1), keypair management, ≤10/day | ❌ **VIOLATED** | Publishing module missing entirely |

**Final determination: 0 of 5 laws fully compliant. This is a total law compliance failure.**

---

## SECURITY CONSENSUS

All three models rated security in the 6-7/10 range — the highest of any subsystem. The ORM baseline is solid. No confirmed exploitable vulnerabilities were identified. Ranked by residual risk:

1. **File-based IPC for relay status (M1)** — Not a direct exploit, but a partial write or race condition could cause the web process to serve malformed JSON. Low CVSS but worth fixing atomically.
2. **No event ID format validation (G3)** — Malformed `event_id` values from a malicious relay could propagate into the DB and cause unpredictable behavior in downstream rendering. Sanitize at ingestion boundary.
3. **Keypair management (when LAW 5 is built)** — The private key for signing Nostr events must be stored securely (environment variable or secrets manager, never in code or DB). This is a future concern but must be designed correctly from the start.
4. **No visible rate limiting on API endpoints** (`/api/nostr/top`, `/api/nostr/relay-status`) — These appear to be public unauthenticated endpoints. Under heavy polling or abuse, they could cause DB load. Add caching layer (even a 30s TTL) on these responses.

---

## WORLD-CLASS GAP CONSENSUS
*(2+ models mentioned — what separates good from exceptional)*

1. **Real-time delivery via WebSockets instead of polling** (Gemini + GPT-4o) — A truly world-class Nostr feed wouldn't make every client hammer an HTTP endpoint every 5 minutes. Server-Sent Events or WebSocket push would provide live updates with dramatically lower server load and a dramatically better user experience.

2. **Robust inter-process communication** (Gemini + GPT-4o + Grok) — Production-grade systems don't use flat JSON files for IPC between a monitor process and a web process. A DB table, Redis pub/sub, or at minimum atomic file writes with a proper schema would be the baseline for a reliable system.

3. **Observable, inspectable monitoring pipeline** (Grok + GPT-4o) — There are no metrics, no health endpoints, no dashboards for the monitor's operational state. A world-class feature would expose: events ingested/sec, relay connection state, queue depth, scoring throughput, and pruning stats — either via a `/health` endpoint or an admin panel section.

4. **Engagement score dynamic updates** (Grok + GPT-4o) — A static score computed once at ingestion time becomes stale immediately. Zap/reaction counts on Nostr events change over time. A world-class implementation would periodically re-query engagement data for recent top-N events and update scores accordingly.

5. **Content quality filtering beyond hashtags** (Grok + Gemini, implicit) — LAW 3 filters by hashtag only. A truly high-quality Bitcoin content feed would layer on spam detection, minimum engagement thresholds before surfacing, author reputation weighting, and possibly semantic relevance scoring to prevent hashtag-spam events from polluting the feed.

---

## FINAL ACTION PLAN

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | **Create `nostr_monitor.py` from scratch** with: asyncio event loop; 4 concurrent WebSocket connections to approved relays; NIP-01 REQ subscription `{kinds:[1,30023], #t:[bitcoin,btc,lightning,nostr,sovereignty]}`; event dedup by ID; in-memory queue max 1000; flush to DB every 60s; exponential backoff reconnect | `nostr_monitor.py` (missing) | **ALL** | Feature is entirely non-functional without this. Violates LAW 2, 3, 4. |
| P0-2 | **Implement LAW 1 scoring** inside ingestion pipeline: `score = zaps*10 + quotes*5 + reposts*3 + replies*2 + reactions*1` | Inside `nostr_monitor.py` | **ALL** | No score computation exists anywhere. DB column is meaningless without it. Violates LAW 1. |
| P0-3 | **Create Nostr publishing service** for Protocol Pulse content: NIP-23 for articles, NIP-1 for videos; sign with managed keypair (from env var); enforce ≤10 posts/day; publish to approved relay list | New module, e.g. `core/services/nostr_publisher.py` | **ALL** | LAW 5 is entirely absent. Critical feature deliverable. |
| P0-4 | **Fix `seed_tracked_pubkeys()` transaction rollback** — move rollback outside loop or use per-row savepoints | `core/services/nostr_service.py:112-115` | **ALL** | Silent data loss bug. Entire batch wiped on any single row error. |
| P0-5 | **Fix invalid seed pubkeys** — correct 3 pubkeys from 63 to 64 hex chars or remove them | `core/services/nostr_service.py:34, 40, 64` | **ALL** | Malformed pubkeys poison author filtering logic. |

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | **Fix scoring formula UI** — update prose to include quotes×5; update legend to include reactions×1 | `core/templates/nostr.html:500-503, 541-554` | **ALL** | Users see materially wrong description of ranking. Violates LAW 1 transparency. |
| P1-2 | **Replace `<canvas>` QR with SVG-based implementation** | `core/templates/nostr.html:515, 650-657` | Gemini + GPT-4o | Direct violation of project stack constraint "NO Canvas". |
| P1-3 | **Fix relay `last_event_at` disappearing on JS refresh** — include field in API response and JS render template | `core/templates/nostr.html:776-779` | GPT-4o + Grok | Regression in UX on first client-side refresh. |
| P1-4 | **Replace flat JSON file IPC with atomic writes or DB table** for relay status | `core/services/nostr_service.py:186-219` | Gemini + GPT-4o | Race condition risk on partial writes; stale data served to users. |
| P1-5 | **Fix `follower_tier` sort** to use SQL CASE expression instead of string sort | `core/services/nostr_service.py:229-232` | Gemini + GPT-4o | Alphabetic sort is brittle and semantically incorrect for tier ordering. |
| P1-6 | **Fix cron import path fragility** — use explicit absolute paths consistent with module structure | `cron/nostr_cron.py:77, 87` | GPT-4o + Grok | Cron may fail to import service silently, making scheduled pruning unreliable. |
| P1-7 | **Add quote count to event card display** — both Jinja and JS render paths | `core/templates/nostr.html:582-593, 739-742` | GPT-4o + Grok (implicit Gemini) | Users cannot see the second-highest weighted score component. |
| P1-8 | **Add event ID format validation** at ingestion boundary | `nostr_monitor.py` (ingestion path) + `core/models.py

---

# WINNER DETERMINATION

WINNER: GPT-4o — Across both cycles, GPT-4o consistently delivered the most granular, evidence-anchored findings: it uniquely identified the invalid 63-char pubkeys, the silent data-loss rollback bug in `seed_tracked_pubkeys()`, the Canvas stack-rule violation, and the string-sort semantic flaw — all of which Gemini and Grok confirmed they missed in their Cycle 2 self-assessments. Its recommendations were the most actionable, citing exact line numbers with specific remediation paths rather than architectural generalities, and it achieved the best balance of breadth (covering all sections) and depth (finding issues others missed).

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by: severity × blast radius × implementation dependency chain.

---

### P0 — FEATURE DOES NOT EXIST (implement first, everything else depends on this)

**P0-A: Create `nostr_monitor.py` from scratch**
- `asyncio` event loop with 4 concurrent WebSocket connections to approved relays
- NIP-01 `REQ` subscription: `kinds: [1, 30023]`, `#t: ['bitcoin', 'btc', 'lightning', 'nostr', 'sovereignty']`
- Event dedup by `id` in-memory set before scoring or DB write
- In-memory queue, max depth 1000, flush to DB every 60s
- Exponential backoff on disconnect (start 1s, cap 60s)
- LAWs violated until fixed: LAW 2, LAW 3, LAW 4

**P0-B: Create publishing service from scratch**
- Read Protocol Pulse content pipeline
- Construct NIP-23 (long-form) and NIP-1 (note) events
- Sign with managed keypair (keypair stored securely, not hardcoded)
- Enforce 10-posts/day rate limit
- LAW violated until fixed: LAW 5

---

### P1 — SILENT DATA CORRUPTION (fix before any seeding runs in production)

**P1-A: Fix rollback-inside-loop bug in `seed_tracked_pubkeys()`**
- File: `core/services/nostr_service.py:95–120`
- Problem: `rollback()` inside the loop discards all prior pending inserts in the session, not just the failed row; `inserted` counter still increments, reporting false success
- Fix: Wrap each insert in a savepoint (`session.begin_nested()`) so only the failing row rolls back; the loop continues and the counter reflects reality

**P1-B: Fix invalid pubkeys in seed list**
- File: `core/services/nostr_service.py:34, 40, 64`
- Problem: Pubkeys are 63 characters, not 64 — invalid for Nostr; any filter or lookup using them silently fails
- Fix: Correct each pubkey to its valid 64-character hex form; add a startup assertion that validates `len(pubkey) == 64` for all seeded values

---

### P2 — CORRECTNESS BUGS IN SHIPPED CODE

**P2-A: Remove Canvas usage — stack rule violation**
- File: `core/templates/nostr.html:515, 650`
- Problem: `<canvas>` is used for QR code generation; project rules explicitly prohibit Canvas
- Fix: Replace with an SVG-based QR library (e.g., `qrcode.js` SVG mode) or a server-side rendered QR image endpoint

**P2-B: Fix string sort on `follower_tier`**
- File: `core/services/nostr_service.py:229–232`
- Problem: `.desc()` on a string column sorts lexicographically (`"gold" > "bronze"` only by accident); will break if tier names change or new tiers are added
- Fix: Add an explicit integer `tier_rank` column to the model, or use a `CASE WHEN` expression in the query to enforce logical sort order

**P2-C: Fix engagement score — scoring logic absent from ingestion path**
- File: `core/models.py:914–937` (fields exist), ingestion path (missing)
- Problem: `engagement_score` is stored but there is no code path that computes it from `zaps*10 + quotes*5 + reposts*3 + replies*2 + reactions*1` (LAW 1) at write time
- Fix: Add a `compute_score()` method on `NostrMonitorEvent` called at flush time in the monitor; never store a score of 0 by default

**P2-D: Fix static scores — no dynamic re-scoring on new engagement data**
- File: `core/services/nostr_service.py:171`
- Problem: Score is set once at fetch time; later engagement on the same event is never reflected
- Fix: Add a scheduled re-score job in `nostr_cron.py` that recalculates `engagement_score` for all events younger than 24h every 15 minutes

---

### P3 — FRAGILITY / RELIABILITY

**P3-A: Replace JSON file IPC for relay status**
- File: `core/services/nostr_service.py:186–219` reads `state/nostr_relay_status.json`
- Problem: No write lock; partial reads possible if monitor crashes mid-write; stale data served silently
- Fix: Replace with a dedicated `NostrRelayStatus` DB table (one row per relay, updated transactionally); fall back to last-known-good row rather than stale file

**P3-B: Fix relay status UI inconsistency on JS refresh**
- File: `core/templates/nostr.html:776–779`
- Problem: Client-side refresh of relay status drops `last_event_at` that was present in server-rendered HTML; field is missing from the API response shape used by the JS update path
- Fix: Add `last_event_at` to the `/api/nostr/relay-status` response payload and render it in the JS update handler

---

### P4 — UI / COPY ACCURACY

**P4-A: Fix scoring formula copy — prose omits quotes multiplier**
- File: `core/templates/nostr.html:500–503`
- Problem: Prose says `zaps 10× > reposts 3× > replies 2× > reactions 1×` — quotes (×5) are absent
- Fix: Update prose to match LAW 1 exactly: `zaps ×10, quotes ×5, reposts ×3, replies ×2, reactions ×1`

**P4-B: Fix scoring legend — legend omits reactions multiplier**
- File: `core/templates/nostr.html:541–553`
- Problem: Legend shows zaps, quotes, reposts, replies but omits reactions (×1)
- Fix: Add reactions row to legend; ensure legend and prose are generated from a single source-of-truth constant to prevent future drift

---

### P5 — IMPLEMENTATION ORDER SUMMARY

```
P0-A (monitor) → P0-B (publisher)
     ↓
P1-A (rollback bug) + P1-B (pubkey validity)   ← run before any seeding
     ↓
P2-C (scoring logic) + P2-D (re-score cron)    ← required for P0-A output to be correct
     ↓
P2-A (canvas) + P2-B (tier sort)               ← correctness, no dependencies
     ↓
P3-A (IPC) + P3-B (UI refresh)                 ← reliability, after monitor exists
     ↓
P4-A + P4-B (copy fixes)                       ← cosmetic, last
```